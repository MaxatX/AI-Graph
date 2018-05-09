# Copyright 2018 The AiGraph LLC, bin.bryandu@gmail.com. All Rights Reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys
import tempfile
import os
import pysftp
import smtplib
import datetime
import csv
import shutil
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import time
import math

from tensorflow.python.platform import gfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from input_data import read_data_sets
from input_data import load_csv_with_header

import tensorflow as tf

FLAGS = None


def deepnn5(x , output_size):
  """deepnn builds the graph for a deep net for classifying digits.

  Args:
    x: an input tensor with the dimensions (N_examples, 288x288=82944), where 82,944 is the
    number of pixels in a standard MNIST image.

  Returns:
    A tuple (y, keep_prob). y is a tensor of shape (N_examples, 10), with values
    equal to the logits of classifying the digit into one of 10 classes (the
    digits 0-9). keep_prob is a scalar placeholder for the probability of
    dropout.
  """
  # Reshape to use within a convolutional neural net.
  # Last dimension is for "features" - there is only one here, since images are
  # grayscale -- it would be 3 for an RGB image, 4 for RGBA, etc.
  with tf.name_scope('reshape'):
    x_image = tf.reshape(x, [-1, 288, 288, 1])
#    tf.summary.image('input', x_image, 3)

  # Added convolutional layer - maps one grayscale image to 96 feature maps.
  with tf.name_scope('conv0'):
    W_conv0 = weight_variable([5, 5, 1, 64])
    b_conv0 = bias_variable([64])
    h_conv0 = tf.nn.relu(conv2d(x_image, W_conv0) + b_conv0)
#    tf.summary.histogram("weights", W_conv0)
#    tf.summary.histogram("biases", b_conv0)
#    tf.summary.histogram("activations", h_conv0)

  # Added Pooling layer - downsamples by 2X.
  with tf.name_scope('pool0'):
    h_pool0 = max_pool_2x2(h_conv0)

  # Add another convolutional layer - maps one grayscale image to 32 feature maps.
  with tf.name_scope('conv00'):
    W_conv00 = weight_variable([3, 3, 64, 96])
    b_conv00 = bias_variable([96])
    h_conv00 = tf.nn.relu(conv2d(h_pool0, W_conv00) + b_conv00)

  # Pooling layer - downsamples by 2X.
  with tf.name_scope('pool00'):
    h_pool00 = max_pool_2x2(h_conv00)

  # Add another convolutional layer - maps one grayscale image to 32 feature maps.
  with tf.name_scope('conv000'):
    W_conv000 = weight_variable([3, 3, 96, 96])
    b_conv000 = bias_variable([96])
    h_conv000 = tf.nn.relu(conv2d(h_pool00, W_conv000) + b_conv000)

  # Pooling layer - downsamples by 2X.
  with tf.name_scope('pool000'):
    h_pool000 = max_pool_2x2(h_conv000)

  # First convolutional layer - maps one grayscale image to 32 feature maps.
  with tf.name_scope('conv1'):
    W_conv1 = weight_variable([3, 3, 96, 96])
    b_conv1 = bias_variable([96])
    h_conv1 = tf.nn.relu(conv2d(h_pool000, W_conv1) + b_conv1)

  # Pooling layer - downsamples by 2X.
  with tf.name_scope('pool1'):
    h_pool1 = max_pool_2x2(h_conv1)

  # Second convolutional layer -- maps 32 feature maps to 64.
  with tf.name_scope('conv2'):
    W_conv2 = weight_variable([3, 3, 96, 128])
    b_conv2 = bias_variable([128])
    h_conv2 = tf.nn.relu(conv2d(h_pool1, W_conv2) + b_conv2)

  # Second pooling layer.
  with tf.name_scope('pool2'):
    h_pool2 = max_pool_2x2(h_conv2)

  # Fully connected layer 1 -- after 2 round of downsampling, our 28x28 image
  # is down to 8x8x64 feature maps -- maps this to 1024 features.
  with tf.name_scope('fc1'):
    W_fc1 = weight_variable([9 * 9 * 128, 1024])
    b_fc1 = bias_variable([1024])

    h_pool2_flat = tf.reshape(h_pool2, [-1, 9*9*128])
    h_fc1 = tf.nn.relu(tf.matmul(h_pool2_flat, W_fc1) + b_fc1)

#    tf.summary.histogram("weights", W_fc1)
#    tf.summary.histogram("biases", b_fc1)
#    tf.summary.histogram("activations", h_fc1)

  # Dropout - controls the complexity of the model, prevents co-adaptation of
  # features.
  with tf.name_scope('dropout'):
    keep_prob = tf.placeholder(tf.float32)
    h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob)

  # Map the 1024 features to 10 classes, one for each digit
  with tf.name_scope('fc2'):
    W_fc2 = weight_variable([1024, output_size])
    b_fc2 = bias_variable([output_size])
    y_conv = tf.matmul(h_fc1_drop, W_fc2) + b_fc2

#    tf.summary.histogram("weights", W_fc2)
#    tf.summary.histogram("biases", b_fc2)
#    tf.summary.histogram("activations", y_conv)

  return y_conv, keep_prob

def conv2d_2_nopad(x, W):
  """conv2d returns a 2d convolution layer with 5 stride and no pad. """
  return tf.nn.conv2d(x, W, strides=[1, 2, 2, 1], padding='VALID')

def conv2d_5_nopad(x, W):
  """conv2d returns a 2d convolution layer with 5 stride and no pad. """
  return tf.nn.conv2d(x, W, strides=[1, 5, 5, 1], padding='VALID')


def conv2d_1_nopad(x, W):
  """conv2d returns a 2d convolution layer with 1 stride and no pad. """
  return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='VALID')

def conv2d(x, W):
  """conv2d returns a 2d convolution layer with full stride."""
  return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')


def max_pool_2x2(x):
  """max_pool_2x2 downsamples a feature map by 2X."""
  return tf.nn.max_pool(x, ksize=[1, 2, 2, 1],
                        strides=[1, 2, 2, 1], padding='SAME')


def weight_variable(shape):
  """weight_variable generates a weight variable of a given shape."""
  initial = tf.truncated_normal(shape, stddev=0.1)
  return tf.Variable(initial)


def bias_variable(shape):
  """bias_variable generates a bias variable of a given shape."""
  initial = tf.constant(0.1, shape=shape)
  return tf.Variable(initial)


def main(_):

  # load data from cacti server
  if ( FLAGS.s != "test" ):
    remotepath = '/usr/share/cacti/plugins/nmidDataExport/export/'
    if not os.path.exists('./data/' + FLAGS.s):
      os.makedirs('./data/' + FLAGS.s)
    localpath = './data/' + FLAGS.s +'/'
    host = FLAGS.s                    
    password = "Denver2758@"                
    username = "dub"     
    print('Download files from', FLAGS.s,remotepath, ' to ', localpath)           
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None    # disable host key checking.    
    with pysftp.Connection(host, username=username, password=password, cnopts=cnopts) as sftp:
      sftp.get_d(remotepath, localpath)
    # Check the modified date for the files. If it is not today file, remove it since cacti nmid doesn't remove old files.
    for fnames in os.listdir(localpath):  
      match = re.search(r'.csv',fnames)
      if( match ):
        (mode, ino, dev, nlink, uid, gid, size, atime,mtime,ctime) = os.stat(localpath + fnames)
        # Delete files older than one hour, doesn't work on Linux file system
        if ( int(time.time() - ctime) > (60*60) ):
          os.remove(localpath + fnames)
          print("Remove ", fnames, " since it is too old. Current time:", time.time(), " Creation time:", ctime)
  else:
    localpath = './data/' + FLAGS.s +'/'

  # Import data
  mnist, num_of_trains, test_files = read_data_sets('no_train', one_hot=True, reshape=True, validation_size=100, image_size=288, output_size=3, test_dir=localpath, train_dir=None)

  # Create the model
  x = tf.placeholder(tf.float32, [None, 82944])

  # Define loss and optimizer
  y_ = tf.placeholder(tf.float32, [None, 3])

  # Build the graph for the deep net
  y_conv, keep_prob = deepnn5(x, output_size=3)

  with tf.name_scope('loss'):
    cross_entropy = tf.nn.softmax_cross_entropy_with_logits(labels=y_,
                                                            logits=y_conv)
  cross_entropy = tf.reduce_mean(cross_entropy)
  tf.summary.scalar("loss", cross_entropy)

  with tf.name_scope('adam_optimizer'):
    train_step = tf.train.AdamOptimizer(1e-5).minimize(cross_entropy)

  with tf.name_scope('accuracy'):
    correct_prediction = tf.equal(tf.argmax(y_conv, 1), tf.argmax(y_, 1))
    correct_prediction = tf.cast(correct_prediction, tf.float32)
  accuracy = tf.reduce_mean(correct_prediction)
  tf.summary.scalar("accuracy", accuracy)

  prediction = tf.argmax(y_conv, 1)

  # Disable GPU because of memory overflow
  config = tf.ConfigProto(device_count = {'GPU': 0})

  summ = tf.summary.merge_all()
  saver = tf.train.Saver()  

  with tf.Session(config=config) as sess:
    sess.run(tf.global_variables_initializer())
    # Restore variables from disk.
    print("Variables restored using",FLAGS.v)
    # Get activation function from the saved collection
    saver.restore(sess, FLAGS.v)

    result = np.empty((0), dtype=int)
    num_of_batch = math.ceil( len(test_files) / 50)
    for i in range(num_of_batch):
      batch = mnist.test.next_batch(50, shuffle=False)
      batch_result = prediction.eval(feed_dict={x: batch[0], y_:batch[1], keep_prob: 1.0}, session=sess)
      result = np.concatenate((result, batch_result), axis=0)

    print("Result array", result)
    map = {0:'Normal', 1:'*Outage', 2:'#Plateau'}
    for i in range(len(test_files) ) :
      # Print the result
      print(map[result[i]], '    \t', test_files[i]);

  # Send an email with abnormal graph links
  sender = "network.performance@viaero.com"
  receiver = FLAGS.e

  # Create message container - the correct MIME type is multipart/alternative.
  msg = MIMEMultipart('related')
  msg['Subject'] = FLAGS.s + ".viaero.net abnormal cacti graphs on " + str(datetime.date.today().month) +'/'+ str(datetime.date.today().day)+'/'+str(datetime.date.today().year) 
  msg['From'] = sender
  msg['To'] = receiver

  # Create the body of the message (a plain-text and an HTML version).
  text = "Hi, this is graph check on cacti on " + str(datetime.date.today().month) +'/'+ str(datetime.date.today().day)+'/'+str(datetime.date.today().year)
  html_start = """\
  <html>
    <head></head>
    <body>
      <p>Hi, the following are AI checked abnormal graphs on cacti in past 24 hours. Let me know if identified graphs are wrong and I can retrain the model.<br>
  """
  html_outage = """        <u>Outage graph links(outrage time > 15m) </u> <br>
  """
  html_plateau = """<br>   <u>Plateau graph links</u> <br>
  """

  # Encapsulate the plain and HTML versions of the message body in an
  # 'alternative' part, so message agents can decide which they want to display.
  msgAlternative = MIMEMultipart('alternative')
  msg.attach(msgAlternative)

  # Create a image directory
  if not os.path.exists('./image/'):
    os.makedirs('./image/')

  for i in range(len(test_files) ) :
    match = re.search(r'_(\d+).csv', test_files[i])
    if match:
      graph_id = match.group(1)
    else:
      continue
    if ( result [i] == 1 ) :
      Title =""
      with gfile.Open(localpath + test_files[i]) as csv_file:
        data_file = csv.reader(csv_file)
        header = next(data_file)
        while (header[0] != 'Date'):
          if (header[0] == "Title:"):
            Title = header[1]
            header = next(data_file)             
        row = next(data_file)                   
        x_start = row[0]
        x = np.arange(0, 24, 1/12)
      html_outage = html_outage + "         " + test_files[i]+ "  "+ Title + """<a href="http://"""+ FLAGS.s+""".viaero.net/cacti/graph.php?action=view&local_graph_id=""" + graph_id + """&rra_id=all">link</a>""" + '<br><img src="cid:image'+ str(i) + '"><br>'
      # Get the data to plot
      array = load_csv_with_header(localpath + test_files[i], 'Date', 288, 1440)
      my_array = np.array(array)
      plt.plot(x, my_array[0:288,0], '-g', x, my_array[0:288, 1], '-b')
      plt.xlabel("Start time is " + x_start)
      plt.fill_between(x, 0, my_array[0:288,0], facecolor='green')
      imagefile = '\''+ test_files[i][0:-4] + '\'.png'
      plt.savefig('./image/'+imagefile)
      plt.close()
      fp = open('./image/' + imagefile, 'rb')
      msgImage = MIMEImage(fp.read())
      fp.close()
      # Define the image's ID as referenced above
      msgImage.add_header('Content-ID', '<image' + str(i) + '>' )
      msg.attach(msgImage)
    elif ( result [i] == 2 ) :
      Title =""
      with gfile.Open(localpath + test_files[i]) as csv_file:
        data_file = csv.reader(csv_file)
        header = next(data_file)
        while (header[0] != 'Date'):
          if (header[0] == "Title:"):
            Title = header[1]
            header = next(data_file)             
        row = next(data_file)                   
        x_start = row[0]
        x = np.arange(0, 24, 1/12)
      html_plateau = html_plateau + "         "  + "         " + test_files[i]+ "  "+ Title + """<a href="http://"""+ FLAGS.s+""".viaero.net/cacti/graph.php?action=view&local_graph_id=""" + graph_id + """&rra_id=all">link</a>""" + '<br><img src="cid:image'+ str(i) + '"><br>'
      # Get the data to plot
      array = load_csv_with_header(localpath + test_files[i], 'Date', 288, 1440)
      my_array = np.array(array)
      plt.plot(x, my_array[0:288,0], '-g', x, my_array[0:288, 1], '-b')
      plt.xlabel("Start time is " + x_start)
      plt.fill_between(x, 0, my_array[0:288,0], facecolor='green')
      imagefile = '\''+ test_files[i][0:-4] + '\'.png'
      plt.savefig('./image/'+imagefile)
      plt.close()
      fp = open('./image/'+imagefile, 'rb')
      msgImage = MIMEImage(fp.read())
      fp.close()
      # Define the image's ID as referenced above
      msgImage.add_header('Content-ID', '<image' + str(i) + '>' )
      msg.attach(msgImage)

  html_end = """
      </p>
    </body>
  </html>
  """

  html = html_start + html_outage + html_plateau + html_end 

  # We reference the image in the IMG SRC attribute by the ID we give it below
  msgText = MIMEText(html, 'html')
  msgAlternative.attach(msgText)

  if ( FLAGS.s != "test" ):
    # Send the message via local SMTP server.
    s = smtplib.SMTP("10.2.57.25")
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(sender, receiver, msg.as_string())
    s.quit()
    # Remove all files in cacti
    shutil.rmtree('./data/' + FLAGS.s)

  shutil.rmtree('./image/')

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--v', type=str,
                      default='pm_graph_variables5.ckpt',
                      help='filename for loading saved variables')
  parser.add_argument('--s', type=str,
                      default='cacti',
                      help='cacti server name or ip address')
  parser.add_argument('--e', type=str,
                      default='bryan.du@viaero.com',
                      help='receiver email address')
  FLAGS, unparsed = parser.parse_known_args()
  tf.app.run(main=main, argv=[sys.argv[0]] + unparsed)
