#!python3
'''
------------------------------------------------------------------------------

------------------------------------------------------------------------------
Developed at: IDIA (Institure for Data Intensive Astronomy), Cape Town, ZA
Inspired by: https://github.com/idia-astro/image-generator

Lennart Heino
------------------------------------------------------------------------------
'''

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import numpy as np
import sys
import logging
import datetime
import os
from glob import glob
from logging import info, error

import click

import casatasks 

from frocc.config import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from frocc.lhelpers import get_dict_from_click_args, DotMap, get_config_in_dot_notation, get_firstFreq, SEPERATOR, SEPERATOR_HEAVY

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)


# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# QUICKFIX

#Otherwise casa log files get confused
import functools
import inspect
def main_timer(func):
    '''
    '''
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        TIMESTAMP_START = datetime.datetime.now()
        info(SEPERATOR_HEAVY)
        info(f"STARTING script: {inspect.stack()[-1].filename}")
        info(SEPERATOR)

        func(*args, **kwargs)

        TIMESTAMP_END = datetime.datetime.now()
        TIMESTAMP_DELTA = TIMESTAMP_END - TIMESTAMP_START
        info(SEPERATOR)
        info(f"END script in {TIMESTAMP_DELTA}: {inspect.stack()[-1].filename}")
        info(SEPERATOR_HEAVY)
    return wrapper

# QUICKFIX
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def call_tclean(channelInputMS, channelNumber, conf, **kwargs):
    '''
    '''
    info(f"Starting CASA tclean for input files: {channelInputMS}")
    info(f"Setting output filename base to: {conf.input.basename + conf.env.markerChannel + channelNumber}")
    imagename = os.path.join(conf.env.dirImages, conf.input.basename + conf.env.markerChannel + channelNumber)

    for kw in kwargs:
        if kw in ('vis', 'imagename', 'niter', 'gain', 'deconvolver',
                  'threshold', 'imsize', 'cell', 'gridder', 'wprojplanes',
                  'specmode', 'spw', 'uvrange', 'stokes', 'weighting',
                  'robust', 'pblimit', 'mask', 'usemask', 'restoration',
                  'restoringbeam'):
            rslt = kwargs.pop(kw)
            if kw in ('niter', 'gain', 'deconvolver',
                      'threshold', 'imsize', 'cell', 'gridder', 'wprojplanes',
                      'specmode', 'spw', 'uvrange', 'stokes', 'weighting',
                      'robust', 'pblimit', 'mask', 'usemask', 'restoration',
                      'restoringbeam'):
                setattr(conf.input, kw, rslt)


    casatasks.tclean(
        vis=channelInputMS,
        imagename=imagename,
        niter=conf.input.niter,
        gain=conf.input.gain,
        deconvolver=conf.input.deconvolver,
        threshold=conf.input.threshold,
        imsize=conf.input.imsize,
        cell=conf.input.cell,
        gridder=conf.input.gridder,
        wprojplanes=conf.input.wprojplanes,
        specmode=conf.input.specmode,
        spw=conf.input.spw,
        uvrange=conf.input.uvrange,
        stokes=conf.input.stokes,
        weighting=conf.input.weighting,
        robust=conf.input.robust,
        pblimit=conf.input.pblimit,
        mask=conf.input.mask,
        usemask=conf.input.usemask,
        restoration=conf.input.restoration,
        restoringbeam=[conf.input.restoringbeam],
        **kwargs
    )
    # export to .fits file
    outImageName = ""
    listCasaImageExtensions = [".image.tt0", ".image"]
    for ext in listCasaImageExtensions:
        if os.path.exists(imagename + ext):
            outImageName = imagename + ".image"
            info(f"CASA image file found: {outImageName}")
        else:
            info(f"CASA image file not found: {imagename + ext}")
    if not outImageName:
        error(f"Could not find CASA image file {imagename} with any of the extensions {listCasaImageExtensions}.")

    outImageFits = outImageName + ".fits"
    info(f"Exporting: {outImageFits}")
    casatasks.exportfits(imagename=outImageName, fitsimage=outImageFits, overwrite=True)


def get_channelNumber_from_slurmArrayTaskId(slurmArrayTaskId, conf):
    '''
    '''
    channelNoList = []
    listing = glob(f"{conf.env.dirVis}/*{conf.env.markerChannel}*")
    for filepath in listing:
        # TODO: make this more generic, be carful with hard code 3 digits
        startIndex = filepath.find(conf.env.markerChannel) + len(conf.env.markerChannel)
        channelNoList.append(filepath[startIndex:startIndex+3])
    channelNoList = sorted(list(set(channelNoList)))

    return channelNoList[int(slurmArrayTaskId)-1]


@click.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
#@click.argument('--inputMS', required=False)
@click.pass_context
@main_timer
def main(ctx, **kwargs):

    args = DotMap(get_dict_from_click_args(ctx.args))
    info("Scripts arguments: {0}".format(args))

    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    info("Scripts config: {0}".format(conf))

    channelNumber = get_channelNumber_from_slurmArrayTaskId(args.slurmArrayTaskId, conf)

    # TODO: help: re-definition of casalog not working.
    # casatasks.casalog.setcasalog = conf.env.dirLogs + "cube_split_and_tclean-" + str(args.slurmArrayTaskId) + "-chan" + str(channelNumber) + ".casa"

    channelInputMS = glob(f"{conf.env.dirVis}/*{conf.env.markerChannel}{channelNumber}*")
    call_tclean(channelInputMS, channelNumber, conf, **kwargs)


if __name__ == "__main__":
    main()
