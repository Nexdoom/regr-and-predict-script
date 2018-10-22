#-*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from enum import Enum

import regression as rg
import service as srv

# ======================================================================================================

EXP_DATA_DIR = r"..\!Data\Exp"
CALC_DATA_DIR = r"..\!Data\Calc"
OUT_DIR = r"..\Out"

# ======================================================================================================

#EXP_NAME = "tg_tanaka_exp_f"
#REGR_FUNC_CALC = "x"
#REGR_FUNC_EXP = "x**0.5+x**-1"

#EXP_NAME = "zahlebivanie"
#REGR_FUNC_CALC = "x"
#REGR_FUNC_EXP = "x"

#EXP_NAME = "shah_jackson_2.1_down"
#REGR_FUNC_CALC = "x**-0.8+x**0.4"
#REGR_FUNC_EXP = "x**-0.4"

#EXP_NAME = "shah_jackson_2.1_up"
#REGR_FUNC_CALC = "x**-1+x**1+x**2+x**3+x**4+x**5+x**6"
#REGR_FUNC_EXP = "x**1+x**-1"

#EXP_NAME = "shah_jackson_7.1_down"
#REGR_FUNC_CALC = "x**-0.5+x**0.5"
#REGR_FUNC_EXP = "x**-0.2+x**0.5"

#EXP_NAME = "shah_jackson_7.1_up"
#REGR_FUNC_CALC = "x**2+x"
#REGR_FUNC_EXP = "x**1+x**-1+x**-2"

#EXP_NAME = "tanrikut_1.2.1_tw"
#REGR_FUNC_CALC = "x+x**-3"
#REGR_FUNC_EXP = "x+x**-3"

#EXP_NAME = "akimoto_exper001"
#REGR_FUNC_CALC = "x"
#REGR_FUNC_EXP = "x"

#EXP_NAME = "akimoto_exper002"
#REGR_FUNC_CALC = "x"
#REGR_FUNC_EXP = "x"

#EXP_NAME = "akimoto_exper003"
#REGR_FUNC_CALC = "x"
#REGR_FUNC_EXP = "x"

#EXP_NAME = "akimoto_exper004"
#REGR_FUNC_CALC = "x"
#REGR_FUNC_EXP = "x"

#REGR_INFO = "x**-1.5"
#REGR_INFO_EXP = ("x**-1.7", 1025.0, "x", 1600.0, "x")
#REGR_INFO_EXP = ("x**-1.7", 1020.0, "x")
#REGR_INFO_CALC = ("x**0.2", 1020.0, "x**-1")

dataset_exp = {"name": "karoutas001_t1",
               "dir": EXP_DATA_DIR,
               "segments_config": ("x**-1.7", 1020.0, "x"),
               "exclude_filters": ()}
#               }

dataset_calc = {"name": "karoutas001_t1",
                "dir": CALC_DATA_DIR,
                "segments_config": ("x**0.2", 1020.0, "x**-1"),
                "exclude_filters": ((2000.0, 3000.0), (1500.0, 900.0),)}
#               }


#dataset_exp = { "name": "karoutas001_t2",
#                "dir": EXP_DATA_DIR,
#                "segments_config": ("x**-1", 1007.0, "x"),
#                "exclude_filters": ((2000.0, 3000.0),) }
#                }
#
#dataset_calc = { "name": "karoutas001_t2",
#                 "dir": CALC_DATA_DIR,
#                 "segments_config": ("x**0.3", 1020.0, "x**-1"),
#                 "exclude_filters": ((2000.0, 3000.0),) }
#                }
# ======================================================================================================

Direction = Enum("Direction", "left right")


class CommonError(Exception):
    pass


class RegrError(Exception):
    pass


def get_nearest_point_index(data, x_value, direction):
    if direction is Direction.left:
        point_index = max(data[x_value >= data["x"]].index.tolist())
    elif direction is Direction.right:
        point_index = min(data[x_value <= data["x"]].index.tolist())

    return point_index


def get_point_indexes_to_drop(data, filters):

    point_indexes = []
    for (initial_left_bnd, initial_right_bnd) in filters:
        initial_filter_desc = "{!s}".format((initial_left_bnd, initial_right_bnd))

        try:
            if isinstance(initial_left_bnd, float):
                left_bnd = get_nearest_point_index(data, initial_left_bnd, Direction.right)
            else:
                left_bnd = initial_left_bnd

            if isinstance(initial_right_bnd, float):
                right_bnd = get_nearest_point_index(data, initial_right_bnd, Direction.left)
            else:
                right_bnd = initial_right_bnd

        except(ValueError):
            raise CommonError("No points to delete in specified range: {}".format(initial_filter_desc))

        if left_bnd > right_bnd:
            raise CommonError("Boundaries are not ascending in specified range: {!s}".format(initial_filter_desc))

        if left_bnd == -1:
            left_point_index = data.index.min()
        else:
            left_point_index = left_bnd

        if right_bnd == -1:
            right_point_index = data.index.max()
        else:    
            right_point_index = right_bnd

        if (left_point_index == 0) or (right_point_index == 0):
            raise CommonError("Zero boundary error. Boundary=0 in specified range: {}".format(initial_filter_desc))

        if (left_point_index < data.index.min()) or (right_point_index > data.index.max()):
            raise CommonError("Filter {0!s} exceeds data range. Data has {1!s} points"
                          .format(initial_filter_desc, max(data.index.tolist())))

        point_indexes.extend(range(left_point_index, right_point_index+1))

    point_indexes = list(set(point_indexes))
    return point_indexes


def get_filtred_data(dataset):
    data = dataset["data"]

    if "exclude_filters" not in dataset:
        return data

    filters = dataset["exclude_filters"]

    data.index += 1

    point_indexes_to_drop = get_point_indexes_to_drop(data, filters)
    data = data.drop(point_indexes_to_drop)

    data.reset_index(drop=True, inplace=True)
    return data


def create_segments(full_data, segments_config):
    if isinstance(segments_config, str):
        segments_config = (segments_config,)

    full_data_bnd_left = full_data["x"].min()
    full_data_bnd_right = full_data["x"].max()

    x_values = [full_data_bnd_left] + \
               [float(val) for val in segments_config if not isinstance(val, str)] + \
               [full_data_bnd_right]

    regr_functions = [val for val in segments_config if isinstance(val, str)]

    segments = []
    for (index, regr_func) in enumerate(regr_functions):
        segment = {"regr_func": regr_func,
                   "bnd_left": x_values[index],
                   "bnd_right": x_values[index+1]}
        segments.append(segment)

    segments = add_data_to_segments(segments, full_data)
    return segments


def add_data_to_segments(segments, full_data):
    for segment in segments:
        segment_data = full_data[(segment["bnd_left"] <= full_data["x"]) &
                                 (full_data["x"] <= segment["bnd_right"])]
        segment_data = segment_data.reset_index(drop=True)
        segment["segment_data"] = segment_data
    return segments


def get_prediction(data_name, regr_func, data, prediction_points):
    regr_result = rg.ols_fit(regr_func, data)
    predictions = rg.get_prediction(regr_result, prediction_points, verbose=True)
#    rg.output_regress_results(data_name, data, regr_result)
#    rg.plot_prediction_data(predictions)
    return predictions


def plot_segments(full_data, segments):
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(full_data["x"], full_data["y"], 'o', label="Data")

    for segment in segments:
        N_PREDICT_POINTS = 100
        prediction_points = np.linspace(segment["bnd_left"],
                                        segment["bnd_right"],
                                        N_PREDICT_POINTS)
        prediction_points = pd.Series(prediction_points, name="x")

        regr_result = rg.ols_fit(segment["regr_func"], segment["segment_data"])
        prediction = rg.get_prediction(regr_result, prediction_points, verbose=True)

        label = "OLS prediction: ({}-{})".format(round(segment["bnd_left"], 1),
                                                 round(segment["bnd_right"], 1))
        ax.plot(prediction["x"], prediction["mean"], '-', label=label)
        ax.legend(loc="best")


if __name__ == "__main__":
    dataset_exp["data"] = rg.load_data_csv(dataset_exp["dir"], dataset_exp["name"], sep=";")
    dataset_calc["data"] = rg.load_data_csv(dataset_calc["dir"], dataset_calc["name"], sep=";")

    dataset_exp["data"] = get_filtred_data(dataset_exp)
    dataset_calc["data"] = get_filtred_data(dataset_calc)

    dataset_exp["segments"] = create_segments(dataset_exp["data"], dataset_exp["segments_config"])
    dataset_calc["segments"] = create_segments(dataset_calc["data"], dataset_calc["segments_config"])

    plot_segments(dataset_exp["data"], dataset_exp["segments"])
    plot_segments(dataset_calc["data"], dataset_calc["segments"])

#    ziped_segments = zip(dataset_exp["segments"], dataset_calc["segments"])
#
#    segment_num = 0
#    for segment_exp, segment_calc in ziped_segments:
#        prediction_points_exp = segment_exp["segment_data"]["x"]
#        prediction_exp = get_prediction(dataset_exp["name"],
#                                        segment_exp["regr_func"],
#                                        segment_exp["segment_data"],
#                                        prediction_points_exp)
#        prediction_exp["mean"].name = "mean_exp"
#
#        prediction_points_calc = segment_exp["segment_data"]["x"]
#        prediction_calc = get_prediction(dataset_calc["name"],
#                                         segment_calc["regr_func"],
#                                         segment_calc["segment_data"],
#                                         prediction_points_calc)
#        prediction_calc["mean"].name = "mean_calc"
#
#        segment_exp["segment_data"]["y"].name = "exp"
#        segment_calc["segment_data"]["y"].name = "CORTES"
#
#        predictions = pd.concat([prediction_exp["x"],
#                                 segment_calc["segment_data"]["y"],
#                                 segment_exp["segment_data"]["y"],
#                                 prediction_exp["mean"],
#                                 prediction_exp["deriv"],
#                                 prediction_exp["mean_ci"],
#                                 prediction_exp["mean_se"],
#                                 prediction_exp["mean_ci_lower"],
#                                 prediction_exp["mean_ci_upper"],
#                                 prediction_exp["mean_se_lower"],
#                                 prediction_exp["mean_se_upper"]],
#                                axis=1)
#
#        print(predictions)
#
#        segment_num += 1
#        segment_exp_name = "{}_segm_{}".format(dataset_exp["name"], str(segment_num))
#        srv.save_dataframe_csv(OUT_DIR, segment_exp_name, predictions, sep=";")
