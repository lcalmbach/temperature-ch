import streamlit as st
import pandas as pd
import numpy as np
import random, string
from datetime import datetime
import time
import base64
from st_aggrid import (
    GridOptionsBuilder,
    AgGrid,
    DataReturnMode,
    GridUpdateMode,
    AgGridTheme,
)
from enum import Enum


def flash_text(text: str, type: str):
    placeholder = st.empty()
    if type == "info":
        placeholder.info(text)
    elif type == "success":
        placeholder.success(text)
    else:
        placeholder.warning(text)
    time.sleep(5)
    placeholder.write("")


def get_random_filename(prefix: str, folder: str, ext: str) -> str:
    """
    Generates a random file by concatenating a folder name, the given
    prefix and the current time to the second and the extension

    Args:
        prefix (str): used to identify the file more easily
        folder (str): folder where file is to be stored
        ext (str): file extension

    Returns:
        str: full path of filename
    """
    # add a trailing / if not present for foldername
    folder = folder + "/" if folder[-1] != "/" else folder
    suffix = datetime.now().strftime("%y%m%d_%H%M%S")
    result = f"{folder}{prefix}-{suffix}.{ext}"
    return result


def random_string(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


def get_base64_encoded_image(image_path):
    """
    returns bytecode for an image file
    """
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def show_save_file_button(p, key: str):
    if st.button("Save png file", key=key):
        filename = get_random_filename("piper", "png")
        export_png(p, filename=filename)
        flash_text(
            f"The plot has been saved to **{filename}** and is ready for download",
            "info",
        )
        with open(filename, "rb") as file:
            btn = st.download_button(
                label="Download image", data=file, file_name=filename, mime="image/png"
            )


def show_table(df: pd.DataFrame, cols=[], settings={}):
    def set_defaults():
        if "height" not in settings:
            settings["height"] = 400
        if "selection_mode" not in settings:
            settings["selection_mode"] = "single"
        if "fit_columns_on_grid_load" not in settings:
            settings["fit_columns_on_grid_load"] = False
        if "update_mode" not in settings:
            settings["update_mode"] = GridUpdateMode.SELECTION_CHANGED

    set_defaults()
    gb = GridOptionsBuilder.from_dataframe(df)
    # customize gridOptions

    gb.configure_default_column(
        groupable=False, value=True, enableRowGroup=False, aggFunc="sum", editable=False
    )
    for col in cols:
        gb.configure_column(
            col["name"], type=col["type"], precision=col["precision"], hide=col["hide"]
        )
    gb.configure_selection(
        settings["selection_mode"], use_checkbox=False
    )  # , rowMultiSelectWithClick=rowMultiSelectWithClick, suppressRowDeselection=suppressRowDeselection)
    gb.configure_grid_options(domLayout="normal")
    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        # theme=AgGridTheme.MATERIAL,
        height=settings["height"],
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=settings["update_mode"],
        fit_columns_on_grid_load=settings["fit_columns_on_grid_load"],
        allow_unsafe_jscode=False,
        enable_enterprise_modules=False,
    )
    selected = grid_response["selected_rows"]
    selected_df = pd.DataFrame(selected)
    # Select first row
    if len(selected_df) == 0:
        selected_df = df[df["id"] == "ALT"]

    return selected_df


def get_domain(df: pd.DataFrame, col_name: str) -> list:
    min_y = df[col_name].min()
    max_y = df[col_name].max()
    return [min_y, max_y]


def get_grid_height(df: pd.DataFrame, max_height: int):
    h = len(df) * cn.AGG_GRID_COL_HEIGHT
    h = max_height if h > max_height else h
    return h


def get_ticks(interval: float, minmax: tuple):
    ticks = int((minmax[1] - minmax[0]) / interval) + 1
    result = [x * interval for x in range(0, ticks)]
    return result


def time_lin_reg(df: pd.DataFrame(), x: str, y: str):
    x = list((df[x] - df[x].min()) / np.timedelta64(1, "D"))
    y = list(df[y])
    linreg = stats.linregress(x, y)
    # days_to_future_date = (future_date - min_date).days
    # extrapol_temperature = linreg.intercept + days_to_future_date * linreg.slope
    return linreg


def add_time_columns(df: pd.DataFrame, time_col: str, cols: list):
    def get_rename_dicts():
        col_dict = {}
        rev_dict = {}
        if "year" in df.columns:
            col_dict["year"] = "_year"
            rev_dict["_year"] = "year"
        if "month" in df.columns:
            col_dict["month"] = "_month"
            rev_dict["_month"] = "month"
        if "day" in df.columns:
            col_dict["day"] = "_day"
            rev_dict["_day"] = "day"
        if len(col_dict) > 0:
            df.rename(columns=col_dict, inplace=True)
        return df, rev_dict

    df, rev_dict = get_rename_dicts()
    if "year_date" in cols:
        df["year"] = df[time_col].dt.year
        df["month"] = 7
        df["day"] = 15
        df["year_date"] = pd.to_datetime(
            df[["year", "month", "day"]],
        )
        df.drop(columns=["year", "month", "day"], axis=1, inplace=True)

    if "month_date" in cols:
        df["year"] = df[time_col].dt.year
        df["day"] = 15
        df["month"] = df[time_col].dt.month
        df["month_date"] = pd.to_datetime(df[["year", "month", "day"]])
        df.drop(columns=["year", "month", "day"], axis=1, inplace=True)
    if len(rev_dict) > 0:
        df.rename(columns=rev_dict, inplace=True)
    if "year" in cols:
        df["year"] = df[time_col].dt.year
    if "month" in cols:
        df["month"] = df[time_col].dt.month
    return df


class ExtendedEnum(Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))
