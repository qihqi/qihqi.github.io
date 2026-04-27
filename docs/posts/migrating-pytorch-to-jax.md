# How to migrate From Nvidia GPU to Google TPU \[Part 2\]

*Published: 2026-04-26*

**Alternative title: How to migrate from PyTorch to Jax**

As mentioned in [previous article](./migrating-nvidia-gpu-to-google-tpu.md), 
One of the biggest mental model shifts if that we need to think about
what computational graphs we are launching on our devices, and their properties.

The questions to answer are:

1. What are the graphs that we are launching?
2. What are the inputs and outputs of the graph?
3. What are the set of shapes+dtypes that these inputs / outputs will be.

Question number 3 is important to avoid recompilations unnecessarily.

Note that, none of the above questions are TPU specific, rather,
they are Jax-specific (or XLA specific), which is great because it means
we can continue this exploration without buying TPUs first.

Let's first focus on a training example.

## Common training setup

Let's go through well understood example: say a training setup like 
the one in https://docs.pytorch.org/tutorials/beginner/introyt/trainingyt.html

In essence, the tutorial from official Pytorch website does the following:

1. Defines a model
2. Defines optimizer
3. Actual train loop:
  a. Load data
  b. run forward pass with data
  c. run backward pass
  d. run optimizer step

The train loop is illustrated in this bit of code (copied from the tutorial above)

```python
def train_one_epoch(epoch_index, tb_writer):
    running_loss = 0.
    last_loss = 0.

    # Here, we use enumerate(training_loader) instead of
    # iter(training_loader) so that we can track the batch
    # index and do some intra-epoch reporting
    for i, data in enumerate(training_loader):
        # Every data instance is an input + label pair
        inputs, labels = data

        # Zero your gradients for every batch!
        optimizer.zero_grad()

        # Make predictions for this batch
        outputs = model(inputs)

        # Compute the loss and its gradients
        loss = loss_fn(outputs, labels)
        loss.backward()

        # Adjust learning weights
        optimizer.step()

        # Gather data and report
        running_loss += loss.item()
        if i % 1000 == 999:
            last_loss = running_loss / 1000 # loss per batch
            print('  batch {} loss: {}'.format(i + 1, last_loss))
            tb_x = epoch_index * len(training_loader) + i + 1
            tb_writer.add_scalar('Loss/train', last_loss, tb_x)
            running_loss = 0.

    return last_loss
```

Now, we want to pin point what are the computational graphs here.
Naively, one might think that just making 3 graphs (forward, backward, optimizer)
is the most easy one. It turns out that it doesn't work. It will become
clear why when we try to define the inputs and outputs of the graph.

The common approach is either 1. One graph with the entire train step.
Or, 2. One forward-backward joint graph, and one optimizer graph.

Let's see what are the inputs and outputs are:

### a single train step

Say, we decided to define one graph for the train step. What inputs 
is needed to do a train step? We can do this by asking the question
on each line of code, what data it needs.

* `output = model(input)` the input part of data, from `(input, label)` pair.
  * But also, implicitly, we need the model's current weight! (those are stored in the model itself)
* `loss = loss_fn(outputs, labels)` this needs the `label` part of data.
  * Technically, It also need the implicit state that when `model(input)` is ran saved, those are needed to do backward, with our *one graph* setup, this part are not considered outside input, as they are generated from the computation within the graph itself. 
* Now optimizer step: it will need the gradients, the weights, and optimizer's internal state.

What about the output? i.e. what are we try to accomplish when running the train step?
Here the model weights are updated in-place, and that is our goal. So the output of our
graph must include the updated weights. We also need to return the updated
optimizer step, because optimizer might keep internal state.

Ok, with the above analysis, we now have that our train step's function signature will look
like this:

```python
def train_step(data, model_weights, opt_state) -> (updated_model_weights, updated_opt_stae)
```

We can also throw in the `loss` there, as even though it is not needed, it's nice to log 
it out to a monitoring service, say Weights and Biases etc. We cannot 
do that inside of `train_step` because `train_step` must be a pure function (i.e. no side effects).

If we need to log out more stuff, say you want to monitor the `abs`-value of norm of gradients to 
detect gradient explosion etc, they right approach is also to return it.
So let's add a `metrics` field to return, that will be a dict containing loss and other metrics.

```python
def train_step(data, model_weights, opt_state) -> (updated_model_weights, updated_opt_state, metrics)
```

Let's meditate on this **pure function** idea a little more. Another property of pure
functions is that the output is completely determined by it's inputs. In otherwords, 
if you want the computation to do something different next time, then pass in a different input.

This is profund when dealing with randomness, as pure function basically says no randomness.
Say if your model uses dropout, and want to drop different things on different train steps, 
or have other random behavior that helps training, then you want to pass in the random
number generator seed in, as another input. 

With all the above information, if I were to rewrite using PyTorch to conform with
pure function requirement, it would look like this:

```python
def train_step(data, model_weights, opt_state, rng):
  torch.manual_seed(rng)
  
  input, label = data
  
  # make a new optimizer to simulate opt logic using passed in state
  optimizer = Optimizer(model_weights)
  optimizer.load_state_dict(opt_state)
  optimizer.zero_grad()
  
  # functional call allows evaluate model with passed in weights
  output = torch.func.functional_call(model, model_weights, args=(input, ))
  loss = loss_fn(output, label)
  loss.backward()
  optimizer.step()
  
  metrics['loss'] = loss
  return model.state_dict(), optimizer.state_dict(), metrics
```

We can feel the crunckyness of writing torch code this way, because, well,
torch assumes you will be doing in-place updates eagerly, and that is not Jax (or XLA or TPU) compatible.
This is not idiomatic or fully runnable PyTorch.

```python
def train_step(rng, data, model_weights, opt_state):
  input, label = data
  
  # this function is a pure function too
  def compute_loss(model_weights, rng, data):
      input, label = data
      # Jax style model is usually a pure function that takes in model_weights already
      output = model(rng, model_weights, input)
      return loss_fn(output, label)
      
  # this function computes gradient wrt the FIRST argument,
  # so it's important to put model_weights as first argument when
  # defining loss_fn above
  grad_fn = jax.value_and_grad(compute_loss) 
  
  loss, grads = grad_fn(model_weights, rng, data)
  
  updates, updated_opt_state = optimizer.update(grads, opt_state)
  updated_weights = optax.apply_update(model_weights, updates)
      
  metrics['loss'] = loss
  return updated_weights, updated_opt_state, metrics
```

Notice that, despite that both looks different, they are actually 
representing the same computation. In other words, it's mostly cosmetic changes.

Now we represented our device computational graph as a Python function. 
The primary way for Jax to define a computational graph is actually exactly
this: define a python pure function.

To compile this function with XLA, we wrap it with `jax.jit`

So our train loop look like:

```python
step_fn_compiled = jax.jit(train_step)
optimizer = optax.adam(0.1)
opt_state = optimizer.init(weights)

rng = ... # defines rng
for i, data in enumerate(dataloader):
  # this generates a new rng each time, so we would run different dropouts on model
  rng, rng_to_use = jax.random.split(rng)
  weights, opt_state, metrics = step_fn_compiled(rng_to_use, data, weights, opt_state)
  if i % 1000 == 999:
      # log out the loss
      tb_writer.add_scalar('Loss/train', metrics['loss'], tb_x)
```

Above we are 1. defining the computational graph (with jax.jit), and 2. repeatedly calling it.
All side effects, such as writing  loss to the dashboard etc, are handled outside of the 
graph.

### Now, think about input shapes

What are the shapes of the inputs? The weights is a `dict` of model weights (or more generally, a [pytree] of model weights), and a model's weights shape are predefined, so their shapes don't change. Same for optimizer state.

So only places that the shapes are variable are in `data`.

The `data` is whatever the training data is stored in the files. So to make sure 
that the shapes are uniform, we need to make sure that the input data have the same shape.

I have seen cases that are not.

For example, for next-token prediction, the input sequence length can be variable length, as
in eager mode, the cross entropy loss is between token (0, n - 1) to token (1, n) and is
equally valid for any n. Or, for image processing, many models can take in images of arbitrary
resolution, and there can be images of different resolution in the training set.

During normal PyTorch training, the variability of training data shapes doesn't matter, but it start
to matter for JAX/XLA. Everytime a different shape is processed, Jax recompiles the graph and it can 
take take a few minutes.

Here the recommendation is to limit how many distinct shapes your graph sees.
For sequences, we can either pad to nearest power of 2 (or some buckets), or concatenate 
sequences too a known shape (say, 8k) with paddings/maskings so that the model can process
many sequences at once. This usually requires changes in the upstream data processing pipeline to 
produce data in this shape (which is outside of the main training loop).

### Few more things to tidy up

With the above excercise, hopefully one will have a good idea what is the effort
of migrating to Jax that is beyond simple syntax remap. A few more things that is useful to add:

#### 1. donating buffer for weights / opt_state.

As currently stands, it actually uses double the memory for weights,
one copy for the weights itself, and one copy for the updated weights that 
`step_fn_compiled` returns. After the returned weight is assigned to weights, 
gc removes one. So the peak memory is double of weights (without according opt_state).

The trick to make `jax` reuse memory which will have the same effect of *inplace update* is 
with `buffer donation`. This way, the function itself is still logically pure function,
just that some inputs will be invalidated after used.

To use it, imply pass `donate_argnums` kwarg to `jax.jit`, see more [here](https://docs.jax.dev/en/latest/buffer_donation.html)

i.e. replace

```python
step_fn_compiled = jax.jit(train_step)
```

with 

```python
step_fn_compiled = jax.jit(train_step, donate_argnums=(2, 3))
```

#### 2. Gradient checkpointing

A common training trick to save memory is gradient checkpoint, 
which is the technique of not saving some intermediate state
required for computing gradients in memory, but recompute them in backward.
This trades compute for memory.

To get that for jax, on simply wrap the loss function with [`jax.checkpoint`](https://docs.jax.dev/en/latest/gradient-checkpointing.html)
before passing it to `jax.value_and_grad`.

One can get *host offloading* with this API as well, which is to save the intermediates in CPU ram
instead of recomputing.

## 2 graph version

I will be brief on the thought process because it's very similar to one step version.
One graph will be:

```python
def forward_backward(weights, data) -> (loss, gradients)
```
and another 

```python
def optimizer_update(weights, gradients, opt_state) -> (updated_weights, updated_opt_state)
```

Both graph are `jax.jit`'d and launched in sequence.

Also a side note on why separating `forward` and `backward` graph does not work:
`forward` graph must return the intermediates needed to compute `backward`,
and `backward` need to take those as input. It's very hard to write code to express 
that cleanly because the intermediates saved are usually hidden by the framework
and is not something cleanly visible. (We can write it out if we have to, though. It's just troublesome).


## Conclusion

Beyond just translating syntax of PyTorch to Jax, we looked at 
how to analyze your existing training loop setup and think of how 
to represent it as repeatedly launch pure computational graph.
Hopefully this can serve you on evaluating how much effort it will take
to migrate to Jax.
