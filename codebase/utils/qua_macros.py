from qm.qua import *
import copy


class ExpVariable:
    """
    This class holds relevant information for a variable of an experiment, including its QUA variable instance and type, the QUA stream to which send the data, and configurations for data saving.
    """

    def __init__(
        self,
        var=None,
        var_type=None,
        stream=None,
        tag=None,
        average=True,
        buffer=True,
        save_all=True,
    ):

        # QUA variable
        self.var = var

        # QUA variable type (int, fixed, bool)
        self.type = var_type

        # QUA stream to which send values
        self.stream = stream

        # Memory tag for saving values
        self.tag = tag

        # Flag for averaging saved values over repetitions
        self.average = average

        # Flag for buffering saved values
        self.buffer = buffer

        # Flag for saving all values to memory
        self.save_all = save_all


def declare_variables(var_list):
    """
    Calls QUA variable declaration statements. Stores QUA variables in var_list and
    returns it.
    """

    for key in var_list.keys():
        if var_list[key].type is None:
            continue

        var_list[key].var = declare(var_list[key].type)

    return var_list


def declare_streams(var_list):
    """
    Calls QUA stream declaration statements. Stores QUA streams in var_list and
    returns it.
    """
    for key in var_list.keys():
        if var_list[key].tag is None:
            continue

        # Declare stream
        var_list[key].stream = declare_stream()

    return var_list


def stream_results(var_list):
    """
    Calls QUA save statement for each ExpVariable object in var_list. Only saves if a
    stream is defined
    """

    for key, value in var_list.items():
        if value.stream is None:
            continue

        save(value.var, value.stream)


def process_streams(var_list, buffer_len=1):
    """
    Save streamed values to memory.
    """

    for key, value in var_list.items():
        if value.stream is None:
            continue

        stream = copy.deepcopy(value.stream)
        memory_tag = value.tag
        if value.buffer:
            stream = stream.buffer(buffer_len)
        if value.average:
            stream = stream.average()
        if value.save_all:
            stream.save_all(memory_tag)
        else:
            stream.save(memory_tag)


def process_Z_values(I_stream, Q_stream, buffer_len=1):
    """
    Use results from I and Q streams to save processed data to memory. Z_SQ_RAW and Z_SQ_RAW_AVG are used for std error calculation; Z_AVG, for plotting.
    """

    # Is and Qs
    I_raw = I_stream.buffer(buffer_len)
    Q_raw = Q_stream.buffer(buffer_len)  # to reshape result streams
    I_avg = I_raw.average()
    Q_avg = Q_raw.average()

    # we need these two streams to calculate  std err in a single pass
    (I_raw * I_raw + Q_raw * Q_raw).save_all("Z_SQ_RAW")
    (I_raw * I_raw + Q_raw * Q_raw).average().save_all("Z_SQ_RAW_AVG")

    # to live plot latest average
    (I_avg * I_avg + Q_avg * Q_avg).save("Z_AVG")
