# How to migrate From Nvidia GPU to Google TPU

*Published: 2026-03-24*

## TL; DR

So I started to summarize what I have learned in the 3 years working for growing 
adoption of TPUs, largely be appearing to PyTorch users. Having worked in both
torch-xla and torchax, and a successful-ish port of vllm to tpu (tpu-inference).

Half way through writing this article, I realized the conclusion that jumps out of the page is:

> To use Google TPU, you want to use Jax.

In other words:

> Migrating to TPU implies migrating to Jax.

and this is actually a good news. Here goes the rest of article.


## Introduction

So you have a ML team training and serving models on GPUs in the Cloud, and 
you are curious about TPUs, for whatever reason.
maybe it's the success of Gemini, maybe it's because Nvidia GPUs are too expensive or sold out,
or maybe, you just want to diversify and not put all eggs on one hardware vendor.

The key question is what does migrating to TPU mean for my team and codebase?
To what extend it is a full rewrite of all the models and infra? OR is a simple device name change
and everything just works? The answer is much more nuanced. However, 
the first step is to understand the TPU computational model and how it differs
from GPU.


## TPU vs. GPU the mental model

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

So now I'd like to state the thesis:

> Migrating to TPU implies migrating to Jax

Note that, the inverse is not true:

> Migrating to Jax implies migrating to TPU

as Jax on GPU is perfectly feasible.


**Aside:** How does frameworks simulated eager model on TPU?

* Case of Jax, it simulates eager mode by launch a small XLA graph for each Jax op,
  this is what happens when you run a jax function without the `jax.jit` decorator.
  The downside of this approach is that it's a slow eager mode. The assumption is that
  it's used only for debugging and any serious users will use `jax.jit`.

* Case of torch-xla, it uses lazy tensor to accumulate the graph (without doing any math yet),
  and launches the graph with few ops accumulated when you actually need the value. This
  is described in detail in the [LazyTensor paper](https://arxiv.org/pdf/2102.13267)


## What this means for Pytorch users

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

What code can avoid the rewrite? The math, including the models themselves, or any algorithm
implemented with pure torch ops that is meant to express the math (not meant to speed things up).

Note that, because PyTorch prevelent eager mode; many model code in the wild has a lots of non-math
components in it's `forward` function. Like logging, writing out metrics to wandb etc, those pieces are likely
need to be rearchitected.

After considering what and how much your existing code are math vs. infra you can start thinking how to 
migrate to Jax. There are roughly 4 strategies you can adopt, (and mix-and-match).

1. Rewrite by hand. After its done, you will have a pure Jax code base.
2. Rewrite with help of LLM agents.
3. Rewrite with help of compiler-based, programatic source-to-source rewrites.
4. Adopt a torch-frontend for Jax, and only rewrite the infra to Jax, and keep the model code in torch.

I will focus on 3 and 4, because the first 2 are pretty straight-forward.
   

If you have a lots of models, and little infra, you can use [torchax](https://google.github.io/torchax/) is the adapter layer 
to Jax. Otherwise, you can fully rewrite to Jax. 

However, regardless which you choose, you are migrating to Jax.
