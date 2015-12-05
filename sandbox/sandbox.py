import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt

from tensorflow.models.rnn import rnn_cell
from tensorflow.models.rnn import seq2seq

input_channels = output_channels = 1
rnn_size = 8 # Number of hidden nodes
# Large batch sizes seem to be MUCH more effective
batch_size = 30  # Number of distinct sequences in a batch
sequence_length = 50  # Length of each sequence in the batch


class RegressionModel(object):
    def inference(self, input_data):
        """
        Build out the graph enough to make predictions
        input_data - a batch of sequences to predict.  Tensor of size [batch_size, input_channels, sequence_length]
        :return: logits
        """

        cell1 = rnn_cell.LSTMCell(rnn_size, input_channels)
        cell2 = rnn_cell.LSTMCell(rnn_size, cell1._output_size, num_proj=output_channels)
        cell = rnn_cell.MultiRNNCell([cell1, cell2])
        # Initial state of the LSTM memory.
        state = tf.zeros([batch_size, cell.state_size])

        inputs = tf.split(2, sequence_length, input_data)  # Slice up the input_data into a list
        inputs = [tf.squeeze(input_, squeeze_dims=[2]) for input_ in inputs]  # Get rid of the dim with size 1

        outputs, states = seq2seq.rnn_decoder(inputs, # decoder_inputs: a list of 2D Tensors [batch_size x cell.input_size]
                                              state,
                                              cell,
                                              None,  # Loop fn
                                              scope='inference'  # Name scope
                                              )

        return outputs, states

    def loss(self, outputs, target_data):
        """
        Build out the graph enough to calculate the loss.  Here we are doing regression so we care about l2 loss.
        output_data - a batch of sequences to predict.  Tensor of size [input_channels, batch_size, n]
        """

        # targets = tf.split(2, sequence_length, target_data)  # Slice up the input_data into a list
        # targets = [tf.squeeze(target_, squeeze_dims=[2]) for target_ in targets]  # Get rid of the dim with size 1

        # assert len(targets) == len(outputs)

        # packed_target = tf.pack(targets)  # packs a list into a tensor
        packed_output = tf.transpose(tf.pack(outputs), perm=[1, 2, 0])

        difference = tf.sub(packed_output, target_data)  # Subtract the target from the actual output

        loss = tf.nn.l2_loss(difference)  # The l2 norm of difference

        return loss

    def train(self, loss, learning_rate):
        # Create the optimizer with the given learning rate.
        # Tried Adam optimizer here, for some reason it's terrible
        optimizer = tf.train.GradientDescentOptimizer(learning_rate)

        # Use the optimizer to apply the gradients that minimize the loss
        # (and also increment the global step counter) as a single training step.
        train_op = optimizer.minimize(loss)

        return train_op

    # How to print out tf variables from a running session
    # v = tf.Variable([1, 2])
    # init = tf.initialize_all_variables()
    #
    # with tf.Session() as sess:
    #    sess.run(init)
    #    # Usage passing the session explicitly.
    #    print v.eval(sess)
    #    # Usage with the default session.  The 'with' block
    #    # above makes 'sess' the default session.
    #    print v.eval()


# IDEA: Train a rnn to output prediction and confidence interval when doing sequence regression.
# What loss function would we use to train this?

def get_sequence(batch_sz, length):
    labels = np.zeros([batch_sz, input_channels, length + 1])
    for i in range(batch_sz):
        labels[i,0] = np.sin(np.linspace(10 * np.random.random(), 10 * np.random.random(), num=length + 1) * 3)
    data = labels  + np.random.normal(size=[batch_sz, input_channels, length + 1]) / 15.
    return data[:, :, :-1], labels[:, :, 1:] # The label is the true next value in the sequence
                                 # Maybe we should give it the noisy next value to be more realistic
                                 # But we don't care because our goal is to train ANY rnn.


def main():
    train_steps = 2500
    data_placeholder = tf.placeholder(tf.float32, shape=(batch_size, input_channels, sequence_length))
    labels_placeholder = tf.placeholder(tf.float32, shape=(batch_size, output_channels, sequence_length))

    model = RegressionModel()

    # Use functions of the model to build the graph

    out, states = model.inference(data_placeholder)
    loss = model.loss(out, labels_placeholder)
    train_op = model.train(loss, 0.00003)

    # Create a session for running Ops on the Graph.
    sess = tf.Session()

    # Run the Op to initialize the variables.
    init = tf.initialize_all_variables()
    sess.run(init)

    for i in range(train_steps):
        data, labels = get_sequence(batch_size, sequence_length)
        feed_dict = {
            data_placeholder: data,
            labels_placeholder: labels
        }

        # Run one step of the model.  The return values are the activations
        # from the `train_op` (which is discarded) and the `loss` Op.  To
        # inspect the values of your Ops or variables, you may include them
        # in the list passed to sess.run() and the value tensors will be
        # returned in the tuple from the call.
        _, loss_value = sess.run([train_op, loss], feed_dict=feed_dict)
        if i % 100 == 0:
            print i, loss_value

    data, labels = get_sequence(batch_size, sequence_length)
    feed_dict = {
            data_placeholder: data,
            labels_placeholder: labels
    }

    vars = sess.run(out + states, feed_dict)
    out_ = vars[0:len(out)]
    states_ = vars[len(out)+1:]

    d = data[0,0,:]
    o = np.array(out_)[:, 0, 0]
    l = labels[0,0,:]

    x1 = range(d.shape[0])
    x2 = range(1, d.shape[0] + 1)
    plt.scatter(x1, d, c='r')
    plt.scatter(x2, o, c='g')
    plt.scatter(x2, l, c='b')
    plt.show()

    print "data third dim", d

    print "out", o
    # print "states", np.array(states_)

    print "labels third dim", l

    # TODO: When the model is trained well the output seems to correlate strongly with the labels
    # but we're off by two.  The last output correlates with the third to last label.


if __name__ == '__main__':
  main()
