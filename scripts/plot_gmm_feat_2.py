#! /usr/bin/python3 -u

import glob
import struct
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from docopt import docopt
import numpy as np
from scipy.stats import multivariate_normal as gauss

def read_gmm(fileGMM):
    '''
       Reads the weights, means and convariances from a GMM
       stored using format "UPC: GMM V 2.0"
    '''

    header = b'UPC: GMM V 2.0\x00'

    try:
        with open(fileGMM, 'rb') as fpGmm:
            headIn = fpGmm.read(15)
    
            if headIn != header:
                print(f'ERROR: {fileGMM} is not a valid GMM file')
                exit(-1)

            numMix = struct.unpack('@I', fpGmm.read(4))[0]
            weights = np.array(struct.unpack(f'@{numMix}f', fpGmm.read(numMix * 4)))

            (numMix, numCof) = struct.unpack('@II', fpGmm.read(2 * 4))
            means = struct.unpack(f'@{numMix * numCof}f', fpGmm.read(numMix * numCof * 4))
            means = np.array(means).reshape(numMix, numCof)

            (numMix, numCof) = struct.unpack('@II', fpGmm.read(2 * 4))
            invStd = struct.unpack(f'@{numMix * numCof}f', fpGmm.read(numMix * numCof * 4))
            covs = np.array(invStd).reshape(numMix, numCof) ** -2

            return weights, means, covs
    except:
        raise Exception(f'Error al leer el fichero {fileGMM}')


def read_fmatrix(fileFM):
    '''
       Reads an fmatrix from a file
    '''
    try:
        with open(fileFM, 'rb') as fpFM:
            (numFrm, numCof) = struct.unpack('@II', fpFM.read(2 * 4))
            data = struct.unpack(f'@{numFrm * numCof}f', fpFM.read(numFrm * numCof * 4))
            data = np.array(data).reshape(numFrm, numCof)

            return data
    except:
        raise Exception(f'Error al leer el fichero {fileFM}')


def pdfGMM(X, weights, means, covs):
    '''
       Returns the probability density function (PDF) of a population X
       given a Gaussian Mixture Model (GMM) defined by its weights,
       means and covariances.
    '''

    pdf = np.zeros(len(X))
    for mix, weight in enumerate(weights):
        try:
            pdf += weight * gauss.pdf(X, mean=means[mix], cov=covs[mix])
        except:
            raise Exception(f'Error al calcular la mezcla {mix} del GMM')

    return pdf

def limsGMM(means, covs, fStd=3):
    '''
       Returns the maximum and minimum values of the mean plus/minus fStd
       times the standard deviation for a set of Gaussians defined by their
       means and convariances.
    '''

    numMix = len(means)

    min_ = means[0][:]
    max_ = means[0][:]

    for mix in range(numMix):
        min_ = np.min((min_, means[mix] - fStd * covs[mix] ** 0.5), axis=0)
        max_ = np.max((max_, means[mix] + fStd * covs[mix] ** 0.5), axis=0)

    margin = max(max_ - min_)

    return min_, max_

def plotGMM(fileGMM1, fileGMM2, xDim, yDim, percents, colorGmm, colorFeat=None, limits=None):
    weights1, means1, covs1 = read_gmm(fileGMM1)
    weights2, means2, covs2 = read_gmm(fileGMM2)
    fig, ax = plt.subplots(2, 2)

    feats1 = np.ndarray((0,2))
    for fileFeat1 in glob.iglob('work/mfcc/BLOCK00/SES002/*.mfcc'):
        feat1 = read_fmatrix(fileFeat1)
        feat1 = np.stack((feat1[..., xDim], feat1[..., yDim]), axis=-1)
        feats1 = np.concatenate((feats1, feat1))

    ax[0,0].scatter(feats1[:, 0], feats1[:, 1], .05, color='darkviolet')
    ax[1,0].scatter(feats1[:, 0], feats1[:, 1], .05, color='darkviolet')


    feats2 = np.ndarray((0, 2))
    for fileFeat2 in glob.iglob('work/mfcc/BLOCK00/SES001/*.mfcc'):
            feat2 = read_fmatrix(fileFeat2)
            feat2 = np.stack((feat2[..., xDim], feat2[..., yDim]), axis=-1)
            feats2 = np.concatenate((feats2, feat2))

    ax[0,1].scatter(feats2[:, 0], feats2[:, 1], .05, color='limegreen')
    ax[1,1].scatter(feats2[:, 0], feats2[:, 1], .05, color='limegreen')

    means1 = np.stack((means1[..., xDim], means1[..., yDim]), axis=-1)
    covs1 = np.stack((covs1[..., xDim], covs1[..., yDim]), axis=-1)

    means2 = np.stack((means2[..., xDim], means2[..., yDim]), axis=-1)
    covs2 = np.stack((covs2[..., xDim], covs2[..., yDim]), axis=-1)

    if not limits:
        min_1, max_1 = limsGMM(means1, covs1)
        limits1 = (min_1[0], max_1[0], min_1[1], max_1[1])
        min_2, max_2 = limsGMM(means2, covs2)
        limits2 = (min_2[0], max_2[0], min_2[1], max_2[1])
    else:
        min_, max_ = (limits[0], limits[2]), (limits[1], limits[3])



    # Fijamos el número de muestras de manera que el valor esperado de muestras
    # en el percentil más estrecho sea 1000. Calculamos el más estrecho como el
    # valor mínimo de p*(1-p)

    numSmp = np.ceil(np.max(1000 / (percents * (1 - percents))) ** 0.5)
    numSmp = int(numSmp);

    x1 = np.linspace(min_1[0], max_1[0], numSmp)
    x2 = np.linspace(min_2[0], max_2[0], numSmp)
    y1 = np.linspace(min_1[1], max_1[1], numSmp)
    y2 = np.linspace(min_2[1], max_2[1], numSmp)
    X1, Y1 = np.meshgrid(x1, y1)
    X2, Y2 = np.meshgrid(x2, y2)


    XX1 = np.array([X1.ravel(), Y2.ravel()]).T
    XX2 = np.array([X2.ravel(), Y2.ravel()]).T

    Z1 = pdfGMM(XX1, weights1, means1, covs1)
    Z1 /= sum(Z1) #NORMALITZAR LA PDF
    Zsort1 = np.sort(Z1)
    Zacum1 = Zsort1.cumsum()
    levels1 = [Zsort1[np.where(Zacum1 > 1 - percent)[0][0]] for percent in percents]

    Z1 = Z1.reshape(X1.shape)

    style = {'colors': ['purple'] * len(percents), 'linestyles': ['-', '-.']}

    CS11 = ax[0,0].contour(X1, Y1, Z1, levels=levels1, **style)
    CS12 = ax[0,1].contour(X1, Y1, Z1, levels=levels1, **style)
    fmt = {levels1[i]: f'{percents[i]:.0%}' for i in range(len(levels1))}
    ax[0,0].clabel(CS11, inline=1, fontsize=14, fmt=fmt)
    ax[0,1].clabel(CS12, inline=1, fontsize=14, fmt=fmt)

    Z2 = pdfGMM(XX2, weights2, means2, covs2)
    Z2 /= sum(Z2) #NORMALITZAR LA PDF
    Zsort2 = np.sort(Z2)
    Zacum2 = Zsort2.cumsum()
    levels2 = [Zsort2[np.where(Zacum2 > 1 - percent)[0][0]] for percent in percents]

    Z2 = Z2.reshape(X2.shape)

    style = {'colors': ['seagreen'] * len(percents), 'linestyles': ['-', '-.']}

    CS21 = ax[1,0].contour(X2, Y2, Z2, levels=levels2, **style)
    CS22 = ax[1,1].contour(X2, Y2, Z2, levels=levels2, **style)
    fmt = {levels2[i]: f'{percents[i]:.0%}' for i in range(len(levels2))}
    ax[1,0].clabel(CS21, inline=1, fontsize=14, fmt=fmt)
    ax[1,1].clabel(CS22, inline=1, fontsize=14, fmt=fmt)


    
    ax[0, 0].set_title(f'GMM: {fileGMM1} Locutor: SES002')
    ax[0, 1].set_title(f'GMM: {fileGMM1} Locutor: SES001')
    ax[1, 0].set_title(f'GMM: {fileGMM2} Locutor: SES002')
    ax[1, 1].set_title(f'GMM: {fileGMM2} Locutor: SES001')

    plt.axis('tight')
    plt.show()
    '''
    ax[0,0].plt.title(f'GMM: {fileGMM1} Locutor SES002')
    ax[0,0].plt.axis('tight')
    ax[0,0].plt.axis(limits)
    ax[0,0].plt.show()

    ax[0,1].plt.title(f'GMM: {fileGMM1} Locutor SES001')
    ax[0,1].plt.axis('tight')
    ax[0,1].plt.axis(limits)
    ax[0,1].plt.show()

    ax[1,0].plt.title(f'GMM: {fileGMM2} Locutor SES002')
    ax[1,0].plt.axis('tight')
    ax[1,0].plt.axis(limits)
    ax[1,0].plt.show()

    ax[1,0].plt.title(f'GMM: {fileGMM2} Locutor SES001')
    ax[1,0].plt.axis('tight')
    ax[1,0].plt.axis(limits)
    ax[1,0].plt.show()
'''



########################################################################################################
# Main Program
########################################################################################################

USAGE='''
Draws the regions in space covered with a certain probability by a GMM.

Usage:
    plotGMM [--help|-h] [options] <file-gmm1> <file-gmm2>

Options:
    --yDim INT, -x INT               'x' dimension to use from GMM and feature vectors [default: 0]
    --xDim INT, -y INT               'y' dimension to use from GMM and feature vectors [default: 1]
    --percents FLOAT..., -p FLOAT...  Percentages covered by the regions [default: 90,50]
    --colorGMM STR, -g STR            Color of the GMM regions boundaries [default: green]
    --colorFEAT STR, -f STR           Color of the feature population [default: red]
    --limits xyLimits -l xyLimits     xyLimits are the four values xMin,xMax,yMin,yMax [default: auto]

    --help, -h                        Shows this message

Arguments:
    <file-gmm1>    File with the first Gaussian mixture model to be plotted
    <file-gmm2>    File with the second Gaussian mixture model to be plotted
'''

if __name__ == '__main__':
    args = docopt(USAGE)

    fileGMM1 = args['<file-gmm1>']
    fileGMM2 = args['<file-gmm2>']
    xDim = int(args['--xDim'])
    yDim = int(args['--yDim'])
    percents = args['--percents']
    if percents:
        percents = percents.split(',')
        percents = np.array([float(percent) / 100 for percent in percents])
    colorGmm = args['--colorGMM']
    colorFeat = args['--colorFEAT']
    limits = args['--limits']
    if limits != 'auto':
        limits = [int(limit) for limit in limits.split(',')]
        if len(limits) != 4:
            print('ERROR: xyLimits must be four comma-separated values')
            exit(1)
    else:
        limits = None

    plotGMM(fileGMM1, fileGMM2, xDim, yDim, percents, colorGmm, colorFeat, limits)

