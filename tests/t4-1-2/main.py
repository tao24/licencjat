# %% IMPORTS
import argparse
import os
from collections import defaultdict

import matplotlib as mpl
mpl.use('agg')
import matplotlib.pyplot as plt
import numpy as np
import torch

from config import DEVICE
from src.data_processing import (Ngram, randomized_ngram,
                                 sequence_loader_MNIST, test_loader_MNIST,
                                 train_loader_MNIST)
from src.history import History
from src.model import Model
# from src.remote import mpl
from src.statistics import get_statistics
from src.training import SGD, SPDG


torch.manual_seed(191735314)
np.random.seed(35492677)

def save(history, model, ngram, optimizer_primal, optimizer_dual, primal_lr, dual_lr, comment=''):
    if not os.path.exists('data'):
        os.mkdir('data')
    fname = 'data/t4-1-2'

    np.save(fname + '_hist', history)
    np.save(fname + '_model', model)
    np.save(fname + '_ngram', ngram)
    np.save(fname + '_opt_primal', optimizer_primal)
    np.save(fname + '_opt_dual', optimizer_dual)
    with open(fname + '_doc', "w+") as doc:
        doc.write("primal_lr: {}\ndual_lr: {}\nn: {}\n{}".format(primal_lr, dual_lr, ngram.n, comment))


def load():
    fname = 'data/t4-1-2'
    hist = np.load(fname + '_hist.npy').item()
    model = np.load(fname + '_model.npy').item()
    ngram = np.load(fname + '_ngram.npy').item()
    opt_primal = np.load(fname + '_opt_primal.npy').item()
    opt_dual = np.load(fname + '_opt_dual.npy').item()
    return hist, model, ngram, opt_primal, opt_dual


continuation = False
num_epochs = 500
save_every = 100
log_every = 100
test_every = 2
primal_lr = 1e-6
dual_lr = 1e-4

show_dual = False
predictions_on_sequences = True
predictions_on_data = False
ngram_data_stats = False
ngram_test_stats = True
loss_on_test = False

# %% CREATING NGRAM
ngram = randomized_ngram(3, 10, out_dim=5, min_var=1e-2)
# ngram = Ngram(3)
# ngram[(0, 1, 2)] = 9.
# ngram[(1, 2, 3)] = 1.
# ngram.norm()
ngram.show()

# %% GENERATING DATASET
data_loader = train_loader_MNIST()
test_loader = test_loader_MNIST()
sequence_loader = sequence_loader_MNIST(ngram, num_samples=50000)
sequence_test_loader = sequence_loader_MNIST(ngram, num_samples=10000)


# %% REGULAR TRAINING (SGD)
# model = Model(ngram)
# model.to(DEVICE)
# model.init_weights()

# optimizer = torch.optim.Adam(model.primal.parameters())
# history = SGD(model, optimizer, data_loader, test_loader, num_epochs=1, log_every=50, test_every=1)

# %% DUAL TRAINING
if continuation:
    history, model, ngram, optimizer_primal, optimizer_dual = load()
    print(model.ngram.n)
else:
    model = Model(ngram, output_size=5)
    model.to(DEVICE)
    model.init_weights()

    optimizer_primal = torch.optim.Adam(model.primal.parameters(), lr=primal_lr)
    optimizer_dual = torch.optim.Adam(model.dual.parameters(), lr=dual_lr)

    history = History()
    for idx in model.dual:
        history['dual ' + str(idx)] = []


epochs_done = 0
while epochs_done < num_epochs:
    history = SPDG(model, optimizer_primal, optimizer_dual, 
                    sequence_loader,
                   data_loader, test_loader, save_every, log_every,
                   test_every,
                   sequence_test_loader=sequence_test_loader, predictions_on_data=predictions_on_data,
                    show_dual=show_dual, predictions_on_sequences=predictions_on_sequences,
                    ngram_data_stats=ngram_data_stats, ngram_test_stats=ngram_test_stats, loss_on_test=loss_on_test,
                   history=history)
    save(history, model, ngram, optimizer_primal, optimizer_dual, primal_lr, dual_lr)
    epochs_done += save_every


# %% PLOTTING 

def plot(predictions, label):
    xs = np.arange(len(predictions)) * test_every
    ys = [[100.0 - preds[i, i] / preds[i].sum() * 100 for preds in predictions] for i in range(model.output_size)]
    mpl.rc('savefig', format='svg')
    mpl.rc('lines', linewidth=0.5)
    mpl.style.use('seaborn')
    for i in range(model.output_size):
        plt.plot(xs, ys[i], label=str(i))
    plt.legend()
    plt.xlabel('Epoch')
    plt.ylabel('Error (%)')
    plt.savefig(f"predictions_{label}_error")
    plt.close()

plot(history.predictions_test, 'test')
if predictions_on_data:
    plot(history.predictions_data, 'data')
if predictions_on_sequences:
    plot(history.predictions_sequences, 'sequences')
