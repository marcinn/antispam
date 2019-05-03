#!/usr/bin/env python
# Copyright (c) 2015 Peixuan Ding
#
# Authors:
#   - Peixuan Ding
#   - Marcin Nowak (small fixes and improvements)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import print_function

import re
import os
import json
from functools import reduce

__version__ = "0.1.0"


class Model(object):
    """Save & Load the model in/from the file system using Python's json
    module.
    """
    def __init__(self, file_path=None):
        """Constructs a Model object by the indicated ``file_path``, if the
        file does not exist, create a new file and contruct a empty model.

        :param file_path: (optional) Path for the model file indicated, if
            path is not indicated, an in memory model is created.

        """
        self.file_path = file_path

        self.spam_count_total = 0
        self.ham_count_total = 0
        self.token_table = {}

        if file_path:
            self.load(file_path)

    def load(self, file_path=None):
        """Load the serialized file from the specified file_path, and return
        ``spam_count_total``, ``ham_count_total`` and ``token_table``.

        :param file_path: (optional) Path for the model file. If the path does
            not exist, create a new one.
        """
        file_path = file_path if file_path else self.file_path
        self.file_path = file_path
        if not os.path.exists(file_path):
            with open(file_path, 'a'):
                os.utime(file_path, None)
        with open(file_path, 'rb') as f:
            data = json.load(f)
            self.spam_count_total = data[0]
            self.ham_count_total = data[1]
            self.token_table = data[2]

    def save(self, file_path=None):
        """Serialize the model using Python's json module, and save the
        serialized modle as a file which is indicated by ``self.file_path``."""
        file_path = file_path or self.file_path
        if not file_path:
            raise ValueError(
                'Model has no file_path defined. '
                'A file_path is required.')
        with open(file_path, 'wb') as f:
            json.dump(
                (self.spam_count_total, self.ham_count_total,
                 self.token_table), f)


class Detector(object):
    """A baysian spam filter

    :param path: (optional) Path for the model file, will be passes to
        ``Model`` and construct a ``Model`` object based on ``path``.
    """
    TOKENS_RE = re.compile(r"\$?\d*(?:[.,]\d+)+|\w+-\w+|\w+", re.U)
    INIT_RATING = 0.4

    def __init__(self, path=None):
        self.model = Model(path)

    def _get_word_list(self, msg):
        """Return a list of strings which contains only alphabetic letters,
        and keep only the words with a length greater than 2.
        """
        return filter(lambda s: len(s) > 2,
                      self.TOKENS_RE.findall(msg.lower()))

    def load(self, file_path):
        self.model.load(file_path)

    def save(self, file_path=None):
        """Save ``self.model`` based on ``self.model.file_path``.
        """
        self.model.save(file_path=file_path)

    def train(self, msg, is_spam):
        """Train the model.

        :param msg: Message in string format.
        :param is_spam: Boolean. If True, train the message as a spam, if
            False, train the message as a ham.
        """
        token_table = self.model.token_table
        if is_spam:
            self.model.spam_count_total += 1
        else:
            self.model.ham_count_total += 1

        for word in self._get_word_list(msg.lower()):
            if word in token_table:
                token = token_table[word]
                if is_spam:
                    token[1] += 1
                else:
                    token[0] += 1
            else:
                token_table[word] = [0, 1] if is_spam else [1, 0]

    def score(self, msg):
        """Calculate and return the spam score of a msg. The higher the score,
        the stronger the liklihood that the msg is a spam is.

        :param msg: Message in string format.
        """
        token_table = self.model.token_table
        hashes = self._get_word_list(msg.lower())
        ratings = []
        for h in hashes:
            if h in token_table:
                ham_count, spam_count = token_table[h]
                if spam_count > 0 and ham_count == 0:
                    rating = 0.99
                elif spam_count == 0 and ham_count > 0:
                    rating = 0.01
                elif (self.model.spam_count_total > 0
                        and self.model.ham_count_total > 0):
                    ham_prob = float(ham_count) / float(
                        self.model.ham_count_total)
                    spam_prob = float(spam_count) / float(
                        self.model.spam_count_total)
                    rating = spam_prob / (ham_prob + spam_prob)
                    if rating < 0.01:
                        rating = 0.01
                else:
                    rating = self.INIT_RATING
            else:
                rating = self.INIT_RATING
            ratings.append(rating)

        if (len(ratings) == 0):
            return 0

        if (len(ratings) > 20):
            ratings.sort()
            ratings = ratings[:10] + ratings[-10:]

        product = reduce(lambda x, y: x * y, ratings)
        alt_product = reduce(lambda x, y: x * y, map(lambda r: 1.0 - r,
                                                     ratings))
        return product / (product + alt_product)

    def is_spam(self, msg):
        """Decide whether the message is a spam or not.
        """
        return self.score(msg) > 0.9


def load(file_path):
    return Detector(file_path)
