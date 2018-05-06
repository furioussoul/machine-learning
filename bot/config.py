DATA_PATH = 'D:\workspace\zimu'
DATA_FILE = 'subtitle.corpus'
CPT_PATH = 'checkpoints'

THRESHOLD = 2

PAD_ID = 0
UNK_ID = 1
START_ID = 2
EOS_ID = 3

BUCKETS = [(19, 19), (28, 28)]

NUM_LAYERS = 3
HIDDEN_SIZE = 128  # 神经元个数

EMB_SIZE = 256  # embedding size
BATCH_SIZE = 128

LR = 0.0005

MAX_GRAD_NORM = 5.0

NUM_SAMPLES = 256


SENTENCE_MAX_LEN = 30

TRAIN_PERCENTAGE = 90
TEST_PERCENTAGE = 10

DATA_SIZE = 5000000


DEC_VOCAB = 115928
ENC_VOCAB = 115928
