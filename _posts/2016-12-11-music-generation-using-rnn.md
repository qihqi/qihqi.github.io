---
layout: post
title:  "Automatic Accompaniment Generation with Seq2Seq"
date:   2016-12-11
tags: machine learning python 
categories: machine learning 
---

*Disclaimer*: This post is the result of the joint work of
[Xuan Zou](https://github.com/zou-xuan) and myself for the final project
_CS294-129: Designing, Visualizing and Understanding Deep Neural Networks_ at 
UC Berkeley.

Background and Problem Statement
------------------------------


When we listen to a song we are usually listening to a rich 
combination sounds with different properties, such as vocals,
chords, melodies or percussions. Usually, a composer and songwriter
first decide on the main melody, and then fill the accompaniment music
with chords and variations, to create a richer musical texture and to
better fit the style it try to convey. 

This [post](http://karpathy.github.io/2015/05/21/rnn-effectiveness/) by 
Andrej Kaparthy has shown the incredible effectiveness of using RNN's
to capture sequential data. So the natural question to ask is, can
RNN be used to create music? The answer is actually yes, as shown in 
[_Composing Music With Recurrent Neural Networks_](
http://www.hexahedria.com/2015/08/03/composing-music-with-recurrent-neural-networks/) 
by Daniel Johnson (2015) and 
[_Magenta_](https://magenta.tensorflow.org/welcome-to-magenta) by 
Google Brain. 

Here we believe that similar techniques can be used to generate accompaniment 
for music. However, because we have a input sequence for melody and 
an output sequence for generated accompaniment, we shall use a 
model that can map sequences to sequences. 

![](/images/manytomany1.png)
![](/images/many2many2.png)

<b>left:</b> arquitecture used for machine translation.
<b>right:</b> arquitecture used for video captioning.

As seen in above image from abovementioned Kaparthy's blog, 
these are 2 ways to map a sequence to another sequence using RNNs
the left one is usually used for 
natural language translation, as described in this 
[paper](https://arxiv.org/abs/1406.1078); by Cho et al., and the right one 
for video captioning.

Primer on RNN and Sequence-to-Sequence
-------------------------------

For readers not familiar with neural networks, 
We can think a vanilla (fully connected) neural cell as a 
functional that takes a vector in \\(R^n\\) and returns a number, i.e. \\(x = f(x)\\). Usually
\\( f \\) is taken to be a linear function followed by a nonlinearity, either the sigmoid function \\( x \mapsto \frac{1}{1+e^x} \\) or the relu \\( x \mapsto \max(x, 0) \\). 
A recurrent neural cell is then a vanilla neural cell with a saved internal state,
so that the output does not only depend on the input, but also the interna state. We can think 
it as a function that acts on sequences \\( (x_1, ..., x_n) \\), with an internal state
sequence \\( (s_1, ..., s_n) \\) returning \\( (y_1, ..., y_n) \\) such that \\( s_i = f(x_i, s_{i-1}) \\) and \\(y_i = g(y_{i+1}) \\); with \\(f \\) usually chosen to be a linear function followed by tanh and \\(g\\) chosen as a linear function.

So, in the picture in the left, the first part tries to collapse the input sequence
to a vector, and then use that vector to try to generate a corresponding sequence, 
which could be of different length. We can 
think the hidden state as a latent space that the sequence truly lives in, and its value
captures the full meaning of the input sequence. While in the right picture, it is saying
that the output of the first timestamp should be the first output, there is a 
tighter orderness between input and output, and the length of then must be the same.
Since music accompaniment, such as chord, usually goes for every 4 or 8 bars, so we have
chosen the first network.


Side note on music data format
------------------------------

Music are stored as full semantic representation, such 
as pdfs of sheet music, or stored as full expressed 
representation, such as raw audio wave. Usually we work
with something in between, like mp3 or MIDI.

### MIDI
MIDIs sits very close to sheet music, as it provides pitches
of individual notes played, but drops the semantic information
on measures and annotations. 

To access the information in MIDI files, we used the 
[python-midi](https://github.com/vishnubob/python-midi)
library.

Then we can use it to see how a midi file looks like:

{% highlight python %}
    import midi
    x = midi.read_midifile('./totalchange2.mid')
    print x[0][:10]

# Output:
#    midi.Track(\
#      [midi.PortEvent(tick=0, data=[0]),
#       midi.TrackNameEvent(tick=0, text='STRING MELODY', data=[83, 84, 82, 73, 78, 71, 32, 77, 69, 76, 79, 68, 89]),
#       midi.ProgramChangeEvent(tick=0, channel=1, data=[48]),
#       midi.ControlChangeEvent(tick=0, channel=1, data=[7, 40]),
#       midi.NoteOnEvent(tick=1760, channel=1, data=[70, 123]),
#       midi.NoteOnEvent(tick=0, channel=1, data=[82, 123]),
#       midi.NoteOnEvent(tick=80, channel=1, data=[82, 0]),
#       midi.NoteOnEvent(tick=0, channel=1, data=[70, 0]),
#       midi.NoteOnEvent(tick=0, channel=1, data=[67, 123]),
#       midi.NoteOnEvent(tick=0, channel=1, data=[79, 123])])
{% endhighlight %}

Above x[0] gives the first track of the midi and [:10] gives the first
10 events of the track. There are all sort of events, here we only
care NoteOnEvent and the corresponding NoteOffEvent(not shown). The first
number in the 'data' field is the instrument key code which maps one-to-one to 
the pitch of the note. 

### Wav

Wave files are how raw audios are recorded. We can read wavs directly into
a numpy array using scipy's io module.

{% highlight python %}
In [12]: import scipy.io.wavfile
In [13]: x = scipy.io.wavfile.read('./1980s-Casio-Piano-C5.wav')
In [14]: x
Out[14]: (44100, array([ 13,   0,   4, ..., -36, -27, -49], dtype=int16))

{% endhighlight %}

Here the first element of the tuple is number of amplitudes per second, and 
the second element is an array that represent the *amplitudes* at a time.


Related Work
------------

Besides forementioned works on music generation, there are
also few works on automatic accompaniment generation.

Lichtenwalter at al. [2008] used sliding window sequential learning
techniques to learn music style for automatic music generation;
Andrej (http://zx.rs/) has presented a Markov-Chain based model
in music generation; and Chen at al. evaluated chord-generation
as a classification problem using simple models. 


Base model
-----------

Originally we thought of using wav format for training, 
as the one of the original goals was to allow user sing or 
hum into the system and get accompaniment out directly, without
need to even write in any musical notation. Curiously all the 
related works mentioned above uses either sheet music or MIDI
as input, so we need to create our own baseline instead of 
just refering the results above.

For baseline model we just used fully connected neural networks
trying to map a vector of amplitudes directly to the corresponding
vector of amplitudes. We have found this nice 
[data set](http://www.cambridge-mt.com/ms-mtk.htm) 
from Cambridge Music Technology’s Multi-track library. This is
a data set used to train people for music mixing.

For preprocessing, we identity the melody track through names,
and merge all the non melody tracks into one. Then we chop the
amplitude vector into a fixed length chunks (say, every 500 values).
Then we train the network with L2 loss, making it to learn the mapping between
those two vectors.

Initially, we thought that the model will not converge at all, as the musical structure
in wav are very subtle. However the model did eventually converge.

#insert loss curve

The produced results have lots of random noise in them, through we could still
find some "musicalness" in them.

Current Model
-------------

After playing around with the base model, we realized that in order 
to use a sequence based model, we have to make sense of
the wav files as a sequence of "characters" or "words". In other words, 
we need to know what are the individual notes, or pitches of the music.
A standard way to get notes from amplitude space data is by using 
fourier transform, to get the signal to frequency space and we can 
then lookup in a table to figure out which musical note it corresponds.

However, using MIDI data we just get that for free. In fact, it turns out 
that MIDI are more widely available than raw wav, probably because people 
usually don't listen to MIDI's for fun, so it doesn't hurt the interest
of the people who are trying to sell music. Also, music in wav form usually
contains features that we don't care for accompaniment generation, such as the 
lyrics of the song, which MIDI doesn't have.

MIDI data can be viewed as list of tracks, and each track has
a TrackNameEvent indicating the instrument the track is played with.
We used a simple heuristics by matching keywords in the instrument name,
and we separate the tracks into 4 categories: "melody", "percussion", "guitar/piano-like"
or "string-like", according to the following:

{% highlight python %}
CLASSES = (
('percussion', 
    ['drums' ,'drum' ,'snare' ,'shaker']),
('guitarlike', 
    ['bass', 'guitar' ,'gtr' ,'banjo', 'piano' ,'keyboard' ,'harp']), 
('stringslike', 
    ['trumpet' ,'organ' ,'flute' ,'sax' ,
     'polysynth' ,'whistle' ,'sax' ,'cello' ,
     'strings' ,'violin']),
('melody', 
    ['words' ,'melody' ,'choir' ,'voice' ,
     'lead' ,'melodie' ,'solo']),
)
{% endhighlight %}

then we trained separate networks with melody vs. percussion and melody vs. guitarlike.
The heuristics is that they both have very different behaviors even having 
the same melody. So it could be easier to learn a simpler patterns than learning all
at once. This is a similar idea to "curricular learning".

To represent the each MIDI file as matrix for training, 
we could try treat those events as "words" in our alphabet, 
to embed those events directly vectors similar to word2vec
used in the original seq2seq for translation, but for us, since we only
care the pitches of the notes, so we used one-hot-vector encoding for the
notes. We restrict the pitch range to 78 distinct notes, which is 6 octaves
(each octave has 12 distinct “half notes”). The result will be a \\(t \\times n\\) matrix,
with \\( t \\) represents which time tick and \\( n\\) represents which notes are on at that
time tick.

After our preparation, we are ready for the training. 
The model consists of 50 LSTM neurons for encoding and 50 for decoding. 

![](https://www.tensorflow.org/versions/r0.8/images/basic_seq2seq.png)
<center>seq2seq diagram from Cho et. al.</center>

Sequence-to-sequence network takes a sequence of equal length as input, 
so we need to reshape our \\( n \\times 78\\) matrix into \\( m \\times l \\times 78\\), 
with \\( m \\times l = n \\)
where we have chosen \\( l = 100\\), in other words, treat 100 notes as a sequence. 

At each mini batch, the LSTM on the encoding side will encode the given melody
into a internal state, which is then feed to the decoder network, in which
should produce an accompaniment. Now we compute the loss as follows: 
\\[
    loss = \\sum \\log( 1 + \\exp(\\frac{y - \hat{y}}{2}))
\\]

In other words, we treat generated vector as the probability 
that a given note is on, so we compare the difference between the
generated notes with the original one by computing the binary crossentropy on
each note and sum all of them. Note that we cannot just use categorical 
crossentropy because there could
be several 1’s in the ground truth.

#losscurve?

After training for a few hours, here is one of the generated samples:

original melody: 

<audio controls>
  <source src="/assets/melody.mid" type="audio/midi">
</audio> 

with accompaniment: 

<audio controls>
  <source src="/assets/totalchange2.mid" type="audio/midi">
</audio> 

Here we combined the generated accompaniment back with the melody. We can 
observe that the accompaniment are relatively simple, having lots of repeated
notes. For percussion it is actually fine, though for chords we might like
more variations. But after all the model gets the beats right.

Tools
-----

For this project we have used [Keras](https://keras.io) 
on [Theano](http://deeplearning.net/software/theano/) to construct seq2seq network.
Similar network for tensorflow can be built as well, as detailed in this 
[tutorial](https://www.tensorflow.org/tutorials/seq2seq/).



Lessons Learned and Future improvements
---------------------------------------

1. Generate music is pretty hard.
2. MIDI works much better than wav, and is easier to get 
   (it is also much more smaller in file size)
3. Our ways to distinguish melody and accompaniment could be better than
   just keyword matching in filenames.
4. By using binary crossentropy on each note, we are treating the event of 
   each note is on as independent events. This is actually not true, because
   even though there could be several notes on at same time because of a chord,
   but it is unlikely to have 30 notes on at the same time. One idea is to add
   a penality when number of on notes are too many, but that could make the loss
   non-differentiable.
5. Another potential improvement is to learn the joint probability of a note is one
   given some other note is on. In other words, build a graphical model with
   each note being a node, and edges represent the probability that 2 notes are on
   at the same time. We can use the MIDI files to estimate the weights on the edges. Then
   use Monte Carlo methods such as Gibbs sampling to get the accompaniment. We can combine
   this and the original network, so that the seq2seq models outputs a single note (so 
   that we can use categorical crossentropy as loss), then use sampling to get a chord.
6. Sometimes part of a accompaniment track actually belongs to melody. For example, in
   a guitar track there are mostly chords, but there can also be a occational solo.
   The solo part should belong to melody. In the current setting, when the guitar solo
   part appears is usually then the melody is mellow, so the model learns a big bias vector
   in their weights because it need to map 0 vector (the silent melody) to a very rich 
   and vary accompaniment (the guitar solo).
7. We can try to incorporate domain knowledge from music theory. This is the approach of
   *Magenta* library. It used comformity to music theory, such as "stay in key" and "don't
   repeat note too much" to compute a reward and used Deep Q learning to train the model.
   This idea potentially can solve the problem that out generated music is too "simple" and
   repetitive.


Site note: Team contribution
----------------------------
Xuan and I did most of the work together physically. We both
contributed equally in finding the source, programming and writeups.
Though Xuan did more preprocessing and I did more model programming.


References:
----------
