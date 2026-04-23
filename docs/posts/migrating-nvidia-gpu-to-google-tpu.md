# How to migrate From Nvidia GPU to Google TPU \[Part 1\]

*Published: 2026-03-24*

## TL; DR

So I started to summarize what I have learned in the 3 years working for growing 
adoption of TPUs, largely be appearing to PyTorch users. I have worked in both
torch-xla and torchax, and a successful-ish port of vllm to tpu (tpu-inference).

Half way through writing this article, I realized the conclusion that jumps out of the page is:

> The work of migrating to TPU is to migrate to Jax.

and this is actually a good thing.


## Introduction

So you have a ML team training and serving models on GPUs in the Cloud, and 
you are curious about TPUs, for whatever reason.
maybe it's the success of Gemini, maybe it's because Nvidia GPUs are too expensive or sold out, or maybe, you just want to diversify and not put all eggs on one hardware vendor.


Now, you hear that migrating to TPU is migrating JAX, and if you are like the most of
GPU users, you are most likely using PyTorch now. So you are like "damn I need to 
rewrite my entire codebase now?" 

The bad news is you need to rewrite a sizable portion, and the good news is that
you want to rewrite those anyways.

The argument goes like this:

  1. The programming model of GPU, as defined by PyTorch, and the programming model
    of TPU, as defined by XLA (the compiler that targets TPU) are fundamentally different.
  2. Therefore, any infra-ish code assuming those model need to be rewritten anyways.
  3. When you rewrite those parts, it's important to adopt the XLA mental model. 
  4. Jax exposes XLA programming model exactly to the user in the most directly controllable way. Therefore it's the best choice.

Besides the technical argument above, there is also a social argument of choosing JAX 
if you have chosen TPU: Google uses it itself. I will not go into details on this argument this time.

## 1. TPU vs. GPU the mental model

**Summary: **

| Dimension | Nvidia GPU | Google TPU |
| --- | --- | --- |
| Execution model | Mostly eager, op-by-op dispatch | Graph capture, compile, then execute |
| Primary abstraction | Strided tensors and imperative tensor ops | Compiler-lowered tensor programs over HLO/StableHLO |
| Mutation model | In-place updates and view semantics are common | Value semantics dominate, mutation is compiler-managed |
| Shape flexibility | Dynamic shapes are more natural | Static or shape-stable programs work best |
| Layout intuition | Strided buffers | Tiled layouts chosen for accelerator execution |
| Performance tuning | Kernel quality, memory traffic, stream behavior | Recompilation control, graph structure, sharding |
| Distributed model | Often one process per device with explicit collectives | Often one process per host with SPMD partitioning |
| Developer mindset | "What kernels am I launching?" | "What program is the compiler building?" |

Let's start with the assumption of you are using PyTorch on GPUs. 

This means that you might have built some in-house framework / infra for using training
PyTorch models or maybe you are using some other libraies like deepspeed or lightning with Pytorch.
Your models are `torch.nn.Module`'s with some torch operators and/or some custom kernel
written using CUDA or triton; but none-the-less, `torch.Tensor` is your data.

This means:

* Your tensor on GPU is strided. (from [ezyang's blog](https://blog.ezyang.com/2019/05/pytorch-internals/))
  * this is not enforced by GPU, it's just how PyTorch chose to implement the tensor.
* strided means many shape manipulations are implemented as `views` (such as transpose / reshape), and can be thought as "free".
* torch ops (Math operations) implemented using CUDA, follows buffer semantic; meaning, in-place mutations on views modify the original tensor, this is used throughly through most of torch programs (i.e. `a[2:4].add_(3)`)
* Use of `torch.as_strided` is possible and signals high-performance, copy-less code.
* Torch mostly uses "eager mode" (for those not using `torch.compile`), meaning that
  code are executed right away as the program run.

Now, let's look at TPU's programming model:

TPU is a glorified matmul machine, it implemented matmul of fixed size in hardware, and have a 
compiler (XLA) that converts a computational graph (using XLA's StableHLO/HLO format) to
programs runnable in TPU. The graph itself is in [static single assignment](https://en.wikipedia.org/wiki/Static_single-assignment_form) form. This means:

* You always uses value semantics: new values are returned from shape manipulations
  and we can treat it as a copy. The compiler will try to eliminate those copies in
  it's bufferization pass, so now it's a must.
* Operators will never mutate inputs, always return a new copy.
* The tensor layout on TPU is tiled.
* No real eager mode. XLA always takes in a graph and compile then run the graph. There are ways to simulate eager mode, which we will expand below.
* Custom kernels is possible using Pallas, however Pallas kernels are still represented in XLA graph (as a custom_call node).
* Graphs are shape-specialized. Meaning, calling functions with inputs of different shapes will cause XLA to recompile.

Now, if we take in their differences in distributed settings, there are more:

On Pytorch+GPU:

* PyTorch will use one process per device (usually started with a launcher like `torchrun` or `slurm`)
* Each device will see local program (shapes are per-device shape)
* Communication ops are explicit in the Python program (either directly using `dist.all_gather` etc, or
  wrapped in some library like DTensor or the torch.dist's FSDP wrapper.)

On TPU, XLA uses SPMD mode, which means:

* Usually you do one process per host, and that process sees all 8 devices on your host.
* You use mesh based API to specify sharding of a tensor (example: https://docs.jax.dev/en/latest/sharded-computation.html).
* You see global shapes in your program
* You can call comm ops directly with [`shard_map`](https://docs.jax.dev/en/latest/notebooks/shard_map.html); but most times comm ops are inserted automatically by
  the compiler.

A good read on how TPUs work is the [Jax scaling book](https://jax-ml.github.io/scaling-book/tpus/)

In other words: The GPU is a generic parallel computing hardware, and PyTorch chose to implement
many of the above property. TPU is a specialized hardware with XLA imposed it's computation model.
You can also implement the XLA-like computation model on GPU; which is Jax-GPU.

In other words, regardless whether you migrate to Jax, or to torch-xla, there gonna 
be a sizable rewrites to acomodate the computational model differences.


**Aside:** How does frameworks simulated eager model on TPU?

* Case of Jax, it simulates eager mode by launch a small XLA graph for each Jax op,
  this is what happens when you run a jax function without the `jax.jit` decorator.
  The downside of this approach is that it's a slow eager mode. The assumption is that
  it's used only for debugging and any serious users will use `jax.jit`.

* Case of torch-xla, it uses lazy tensor to accumulate the graph (without doing any math yet),
  and launches the graph with few ops accumulated when you actually need the value. This
  is described in detail in the [LazyTensor paper](https://arxiv.org/pdf/2102.13267)


## 2. What code must be rewritten no-matter-what

If you are a PyTorch users and have a bunch of code written for Pytorch
then chances are you need to rewrite some of the code. There is one kind 
of code that you cannot avoid in rewriting (or deleting): those whose goal is to make
model fast on GPU. This means:

* custom CUDA/triton kernels. Luckily for this category, popular kernels such as `flash_attention`
  usually have a Pallas implementation for TPU already.
* infra code that manages the processes for distributed code (remember TPU is one process per host now).
* memory optimizations such as pre-allocating a big GPU memory and using `torch.as_strided` to view as
  many tensors.
* Overall train loop; because now you need to be aware of the shape change and recompilation.

What code can you theoretically avoid the rewrite? The math, 
including the models themselves, or any algorithm expressed with pure torch ops that is meant to express the math. Wait a minute, but if we migrate to JAX, don't we have to rewrite this part too? Well this is the bit that you can get away with `torchax`, more on that later.

Note that, because PyTorch prevelent eager mode; many model code in the wild has a lots of non-math
components in it's `forward` function. Like logging, writing out metrics to wandb etc, those pieces are likely
need to be rearchitected.

After considering what and how much your existing code are math vs. infra you can start thinking how to 
migrate to Jax. There are roughly 4 strategies you can adopt, (and mix-and-match).

1. Rewrite by hand. After its done, you will have a pure Jax code base.
2. Rewrite with help of LLM agents.
3. Rewrite with help of compiler-based, programatic source-to-source rewrites. i.e. [ml-switcheroo](https://github.com/SamuelMarks/ml-switcheroo)
4. Adopt a torch-frontend for Jax, and only rewrite the infra to Jax, and keep the model code in torch. i.e. [torchax](https://google.github.io/torchax/)

If you have a lots of models, and little infra, you can use [torchax] is the adapter layer 
to Jax. Otherwise, you can fully rewrite to Jax. 

However, regardless which you choose, you are migrating to Jax.


## 3. How should one choose?

Let's go through few scenarios:

### 1. You are a model builder with a handful of models 

Say, you are fundation model builder like Anthropic. You have one model that is your product (probably with different
variants / sizes, but it's architecture-wise one model (one `torch.nn.Module`)). However, to train this model, you might have a very complex
infra setup in managing the clusters, fault tolerances, implementing different
parallelisms etc etc. 

As we covered above, if you migrate to TPU, all the infra stuff will need to 
rewritten, and you actually want that, you want to squeeze out the performance
of TPU, so you want to do things the TPU way.

Now, the model definition itself is actually small part of your codebase, so you might
as well as rewrite it. You can get started with pointing your favorite 
LLM agent to it, or just discard it and start by forking a high quality Jax 
reference implementation, like [maxtext](https://github.com/AI-Hypercomputer/maxtext) for LLMs
and [maxdiffusion](https://github.com/AI-Hypercomputer/maxdiffusion) and go from there.

### 2. You have your own ML framework that is implemented on top of torch

Say you implemented your own abstraction on top of torch, so your researchers
define their model and train loop in terms of your homegrown ML library. Torch 
is used to implement a backend of your ML library.

In such case, you can implement a backend for your library in Jax. If your library
did not expose too much torchiness, that should not be too hard, and everyone using
your framework can work unchanged. This is of course an very idealistic scenario.

### 3. You have many many models built by different teams, but they share the infra.

For this scenario maybe using torchax as an adapter layer is favorable. You can 
rebuild the infra layer in Jax, and keep the model definitions the same. In this scenario
the purer the model (i.e. just math) the better.


## 4. Why is having to move to JAX a good thing?

As I said, framing the problem as: "I need to migrate from Pytorch to JAX, let me figure 
out how and many much it costs", is an easier problem to solve vs. "I need to migrate from GPU
to TPU".

Here is why, first of all, if you frame it as a GPU -> TPU problem, first you need
to get some TPUs. That means start talking to Google cloud sales, getting provisions,
getting your engineers to use google cloud, then TPU software ecosystem etc etc. 
However, if you frame it as a ML framework migration, you can start right a way! 
Because, JAX runs perfectly fine on GPU! Sure, getting Jax running on GPU
does not automatically imply it runs on TPU (because of custom CUDA kernels and such), but 
the delta is known, and bounded.

Second of all, your engineers can make a much accurate estimate on what it cost 
to migrate to a different library than migrating to a hardware that the engineer hasn't
used. The estimate number can be large, but known large number is much better than unknown.

Third, Agents. AI Agents work best then it can verify the work and iterate. You can test
a torch and Jax problem side-by-side on the same GPU machine.

Fourth, moving to Jax actually have other benefits other than unlocks multi-hardware. I'll
not expand here.

## 5. What if I insist on using torch on TPU?

Torch on TPU as something that has same programming model as PyTorch-CUDA simply
does not exist. Your choice here are to use [torch-xla](https://github.com/pytorch/xla) or [torchax](https://github.com/google/torchax). 

Having worked on both projects, my key insight on their philosophical differences are:
* torch-xla tries to hide the fact that there is a graph compilation going on, by abstracting
  it behind lazy-tensor.
* torchax explicitly exposes the Jax-ness and `jitting`.

This philosophical difference means that getting top performance in torch-xla
is more challenging, because you don't really know when it recompiles, and what 
is the graph fragment it recompiled. You can trying to poke holes on the abstraction
trying to get inner details, but if you do, then the abstraction becomes leaky and get
in the way.
