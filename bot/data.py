import os
import random
import re
import random
import sys
import nltk
import itertools
from collections import defaultdict
import numpy as np
import jieba as jb
import pickle

import config

regex_cn = "^[\u4E00-\u9FA5]+$"


def read_lines(filename):
    return open(filename, encoding='utf-8').read().split('\n')[:config.DATA_SIZE]


def line_ids(line, lookup, maxlen):
    indices = []
    for word in line:
        if word in lookup:
            indices.append(lookup[word])
        else:
            indices.append(lookup[config.UNK_ID])
    return indices


def _pad_input(input_, size):
    return input_ + [config.PAD_ID] * (size - len(input_))


def _reshape_batch(inputs, size, batch_size):
    """ Create batch-major inputs. Batch inputs are just re-indexed inputs
    """
    batch_inputs = []
    for length_id in range(size):
        batch_inputs.append(np.array([inputs[batch_id][length_id]
                                      for batch_id in range(batch_size)], dtype=np.int32))
    return batch_inputs


def build_vocab(vocab, lines):
    for line in lines:
        for word in line:
            if word not in vocab:
                vocab[word] = 0
            vocab[word] += 1
    return vocab


def build_id2word(vocab):
    id2word = {}
    for (k, v) in vocab.items():
        id2word[v] = k
    return id2word


def process_raw_data():
    file_path = os.path.join(config.DATA_PATH, config.DATA_FILE)
    lines = read_lines(filename=file_path)

    qlines = []
    alines = []

    for i in range(0, len(lines), 2):
        if i + 1 == len(lines):
            break
        if re.match(regex_cn, lines[i]) and re.match(regex_cn, lines[i + 1]):
            qlines.append(lines[i])
            alines.append(lines[i + 1])

    questions = [[w for w in jb.cut(wordlist)] for wordlist in qlines]
    answers = [[w for w in jb.cut(wordlist)] for wordlist in alines]

    vocab = build_vocab({},questions)
    vocab = build_vocab(vocab,answers)

    id2word = [' '] + [config.UNK_ID] + [x for x in vocab]
    word2id = dict([(w, i) for i, w in enumerate(id2word)])

    with open('config.py', 'a') as cf:
        cf.write('DEC_VOCAB = ' + str(len(id2word)) + '\n')
        cf.write('ENC_VOCAB = ' + str(len(id2word)) + '\n')

    questions_ids = [line_ids(word, word2id, config.SENTENCE_MAX_LEN) for word in questions]
    answers_ids = [line_ids(word, word2id, config.SENTENCE_MAX_LEN) for word in answers]

    np.save(config.DATA_PATH + '/idx_q.npy', questions_ids)
    np.save(config.DATA_PATH + '/idx_a.npy', answers_ids)

    metadata = {
        'w2idx': word2id,
        'idx2w': id2word
    }
    with open(config.DATA_PATH + '/metadata.pkl', 'wb') as f:
        pickle.dump(metadata, f)

    return id2word, word2id, questions_ids, answers_ids


def load_data():
    # read data control dictionaries
    with open(config.DATA_PATH + '/metadata.pkl', 'rb') as f:
        metadata = pickle.load(f)
    # read numpy arrays
    idx_q = np.load(config.DATA_PATH + '/idx_q.npy')
    idx_a = np.load(config.DATA_PATH + '/idx_a.npy')

    c = list(zip(idx_q, idx_a))

    random.Random().shuffle(c)

    idx_q, idx_a = zip(*c)

    return metadata, idx_q, idx_a


def load_bucket_data(encode_ids, decode_ids, max_training_size=None):
    train_data_buckets = [[] for _ in config.BUCKETS]
    test_data_buckets = [[] for _ in config.BUCKETS]
    i = 0
    for i in range(int(len(encode_ids) * (config.TRAIN_PERCENTAGE / 100))):
        encode_id = encode_ids[i]
        decode_id = decode_ids[i]
        for bucket_id, (encode_max_size, decode_max_size) in enumerate(config.BUCKETS):
            if len(encode_id) <= encode_max_size and len(decode_id) <= decode_max_size:
                train_data_buckets[bucket_id].append([encode_id, decode_id])
                break

    j = i
    i = 0
    for i in range(j, len(encode_ids)):
        encode_id = encode_ids[i]
        decode_id = decode_ids[i]
        for bucket_id, (encode_max_size, decode_max_size) in enumerate(config.BUCKETS):
            if len(encode_id) <= encode_max_size and len(decode_id) <= decode_max_size:
                test_data_buckets[bucket_id].append([encode_id, decode_id])
                break
    return train_data_buckets, test_data_buckets


def sentence2id(sentence, vocab):
    sentence = jb.cut(sentence)
    return [vocab[word] for word in sentence]


def get_batch(data_bucket, bucket_id, batch_size=1):
    """ Return one batch to feed into the model """
    # only pad to the max length of the bucket
    encoder_size, decoder_size = config.BUCKETS[bucket_id]
    encoder_inputs, decoder_inputs = [], []

    for _ in range(batch_size):
        encoder_input, decoder_input = random.choice(data_bucket)
        # pad both encoder and decoder, reverse the encoder
        encoder_inputs.append(list(reversed(_pad_input(encoder_input, encoder_size))))
        decoder_inputs.append(_pad_input(decoder_input, decoder_size))

    # now we create batch-major vectors from the data selected above.
    batch_encoder_inputs = _reshape_batch(encoder_inputs, encoder_size, batch_size)
    batch_decoder_inputs = _reshape_batch(decoder_inputs, decoder_size, batch_size)

    # create decoder_masks to be 0 for decoders that are padding.
    batch_masks = []
    for length_id in range(decoder_size):
        batch_mask = np.ones(batch_size, dtype=np.float32)
        for batch_id in range(batch_size):
            # we set mask to 0 if the corresponding target is a PAD symbol.
            # the corresponding decoder is decoder_input shifted by 1 forward.
            if length_id < decoder_size - 1:
                target = decoder_inputs[batch_id][length_id + 1]
            if length_id == decoder_size - 1 or target == config.PAD_ID:
                batch_mask[batch_id] = 0.0
        batch_masks.append(batch_mask)
    return batch_encoder_inputs, batch_decoder_inputs, batch_masks


if __name__ == '__main__':
    process_raw_data()