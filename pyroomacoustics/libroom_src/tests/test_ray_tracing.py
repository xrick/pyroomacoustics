import numpy as np
import pyroomacoustics as pra
from pyroomacoustics.utilities import fractional_delay
import matplotlib.pyplot as plt
import time
import scipy
from scipy.io import wavfile
from scipy import signal
from pyroomacoustics import build_rir

wall_corners_strange = [
    np.array([  # front
        [0, 3, 3, 0],
        [0, 0, 0, 0],
        [0, 0, 2, 2],
    ]),
    np.array([  # back
        [0, 0, 6, 6],
        [8, 8, 8, 8],
        [0, 4, 4, 0],
    ]),
    np.array([  # floor
        [0, 0, 6, 3, ],
        [0, 8, 8, 0, ],
        [0, 0, 0, 0, ],
    ]),
    np.array([  # ceiling
        [0, 3, 6, 0, ],
        [0, 0, 8, 8, ],
        [2, 2, 4, 4, ],
    ]),
    np.array([  # left
        [0, 0, 0, 0, ],
        [0, 0, 8, 8, ],
        [0, 2, 4, 0, ],
    ]),
    np.array([  # right
        [3, 6, 6, 3, ],
        [0, 8, 8, 0, ],
        [0, 0, 4, 2, ],
    ]),
]

wall_corners_cube = [
    np.array([  # front
        [0, 10, 10, 0],
        [0, 0, 0, 0],
        [0, 0, 10, 10],
    ]),
    np.array([  # back
        [0, 10, 10, 0],
        [10, 10, 10, 10],
        [0, 0, 10, 10],
    ]),
    np.array([  # floor
        [0, 0, 10, 10, ],
        [0, 10, 10, 0, ],
        [0, 0, 0, 0, ],
    ]),
    np.array([  # ceiling
        [0, 0, 10, 10, ],
        [0, 10, 10, 0, ],
        [10, 10, 10, 10, ],
    ]),
    np.array([  # left
        [0, 0, 0, 0, ],
        [0, 0, 10, 10, ],
        [0, 10, 10, 0, ],
    ]),
    np.array([  # right
        [10, 10, 10, 10, ],
        [0, 10, 10, 0, ],
        [0, 0, 10, 10, ],
    ]),
]

absorptions = [0.01]*len(wall_corners_strange)


def test_room_construct(cube):

    # Choose which room to use
    if cube :
        walls = [pra.libroom_new.Wall(c, a) for c, a in zip(wall_corners_cube, absorptions)]
        obstructing_walls = []
        microphones = np.array([
            [6., ],
            [8., ],
            [5., ],
        ])

        room = pra.libroom_new.Room(walls, obstructing_walls, microphones)

    else :
        walls = [pra.libroom_new.Wall(c, a) for c, a in zip(wall_corners_strange, absorptions)]
        obstructing_walls = []
        microphones = np.array([
            [2.5, ],
            [7, ],
            [1., ],
        ])

        room = pra.libroom_new.Room(walls, obstructing_walls, microphones)

    return room

def compute_rir(log, time_thres, fs, plot=True):
    # TIME = 0
    # ENERGY = 1
    #
    # time = np.array([e[TIME] for e in log], dtype=np.float)
    # alpha = np.array([e[ENERGY] for e in log], dtype=np.float)
    # visibility = np.ones(time.shape[0], dtype=np.int32)
    #
    # # ======= WITH FRACTIONAL PART =======
    #
    # # the python utilities to compute the rir
    # fdl = pra.constants.get('frac_delay_length')
    # fdl2 = (fdl - 1) // 2  # Integer division
    #
    # ir = np.zeros(int(time_thres * fs) + fdl)
    #
    # print(np.floor(fs * np.min(time)) - fdl2)
    #
    #
    # build_rir.fast_rir_builder(ir, time, alpha, visibility, fs, fdl)
    #
    # if plot:
    #     x = np.arange(len(ir)) / fs
    #     plt.figure()
    #     plt.plot(x, ir)
    #     plt.title("RIR")
    #     plt.show()
    #
    # return ir


    TIME = 0
    ENERGY = 1

    # ======= WITH FRACTIONAL PART =======

    # the python utilities to compute the rir
    fdl = pra.constants.get('frac_delay_length')
    fdl2 = (fdl - 1) // 2  # Integer division

    ir = np.zeros(int(time_thres * fs) + fdl)

    for entry in log:
        time_ip = int(np.floor(entry[TIME] * fs))

        if time_ip > len(ir) - fdl2 or time_ip < fdl2:
            continue

        time_fp = (entry[TIME] * fs) - time_ip

        # Distance attenuation
        ir[time_ip - fdl2:time_ip + fdl2 + 1] += (entry[ENERGY] * fractional_delay(time_fp))


    if plot :
        x = np.arange(len(ir)) / fs
        plt.figure()
        plt.plot(x, ir)
        plt.title("RIR")
        plt.show()

    return ir

def apply_rir(rir, wav_file_name, fs, cutoff=200, result_name="aaa.wav"):


    fs0, audio_anechoic = wavfile.read(wav_file_name)


    if len(audio_anechoic.shape) > 1 :
        audio_anechoic = audio_anechoic[:,0]

    audio_anechoic = audio_anechoic - np.mean(audio_anechoic)

    # Compute the convolution and set all coefficients between -1 and 1 (range for float32 .wav files)
    result = scipy.signal.fftconvolve(rir, audio_anechoic)

    if cutoff > 0:
        result = highpass(result, fs, cutoff)

    result /= np.abs(result).max()
    result -= np.mean(result)
    wavfile.write(result_name, rate=fs, data=result.astype('float32'))

def highpass(audio, fs, cutoff=200, butter_order=5):
    nyq = 0.5 * fs
    fc_norm = cutoff / nyq
    b, a = signal.butter(butter_order, fc_norm, btype="high", analog=False)
    return signal.lfilter(b, a, audio)


if __name__ == '__main__':

    cube = True
    room = test_room_construct(cube)

    # parameters
    nb_phis = 100
    nb_thetas = 100

    #Good one
    source_pos = [1.5,0.5,0.5]

    #Wrong one to test exception
    #source_pos = [400,500,3]

    mic_radius = 0.5


    scatter_coef = 0.


    time_thres = 0.8 #s
    sound_speed = 340

    fs = 16000

    # compute the log with the C++ code
    chrono = time.time()
    log = room.get_rir_entries(nb_phis, nb_thetas, source_pos, mic_radius, scatter_coef, time_thres, sound_speed)
    print(nb_phis*nb_thetas, " rays traced in ", time.time()-chrono, " seconds" )
    print(len(log), " entries to build the rir")


    rir = compute_rir(log, time_thres, fs, plot=True)

    apply_rir(rir, "0riginal.wav", fs, cutoff=0)




