import numpy as np

# import pandas as pd
import scipy.signal
import xarray as xr

from . import utils


def trim_min(ds, var):
    if var + "_min" in ds.attrs:
        print("%s: Trimming using minimum value of %f" % (var, ds.attrs[var + "_min"]))
        ds[var] = ds[var].where(ds[var] >= ds.attrs[var + "_min"])

        notetxt = "Values filled where less than %f units. " % ds.attrs[var + "_min"]

        ds = utils.insert_note(ds, var, notetxt)

    return ds


def trim_max(ds, var):
    if var + "_max" in ds.attrs:
        print("%s: Trimming using maximum value of %f" % (var, ds.attrs[var + "_max"]))
        ds[var] = ds[var].where(ds[var] <= ds.attrs[var + "_max"])

        notetxt = "Values filled where greater than %f units. " % ds.attrs[var + "_max"]

        ds = utils.insert_note(ds, var, notetxt)

    return ds


def trim_min_diff(ds, var):
    if var + "_min_diff" in ds.attrs:
        print(
            "%s: Trimming using minimum diff of %f" % (var, ds.attrs[var + "_min_diff"])
        )
        ds[var][np.ediff1d(ds[var], to_begin=0) < ds.attrs[var + "_min_diff"]] = np.nan

        notetxt = (
            "Values filled where data decreases by more than %f "
            "units in a single time step. " % ds.attrs[var + "_min_diff"]
        )

        ds = utils.insert_note(ds, var, notetxt)

    return ds


def trim_max_diff(ds, var):
    if var + "_max_diff" in ds.attrs:
        print(
            "%s: Trimming using maximum diff of %f" % (var, ds.attrs[var + "_max_diff"])
        )
        ds[var][np.ediff1d(ds[var], to_begin=0) > ds.attrs[var + "_max_diff"]] = np.nan

        notetxt = (
            "Values filled where data increases by more than %f "
            "units in a single time step. " % ds.attrs[var + "_max_diff"]
        )

        ds = utils.insert_note(ds, var, notetxt)

    return ds


def trim_med_diff(ds, var):
    if var + "_med_diff" in ds.attrs:
        if "kernel_size" in ds.attrs:
            kernel_size = ds.attrs["kernel_size"]
        else:
            kernel_size = 5
        print(
            "%s: Trimming using %d-point median filter diff of %f"
            % (var, kernel_size, ds.attrs[var + "_med_diff"])
        )
        filtered = scipy.signal.medfilt(ds[var], kernel_size=kernel_size)
        bads = np.abs(ds[var] - filtered) > ds.attrs[var + "_med_diff"]
        ds[var][bads] = np.nan

        notetxt = (
            "Values filled where difference between %d-point "
            "median filter and original values is greater than "
            "%f. " % (kernel_size, ds.attrs[var + "_med_diff"])
        )

        ds = utils.insert_note(ds, var, notetxt)

    return ds


def trim_med_diff_pct(ds, var):
    if var + "_med_diff_pct" in ds.attrs:
        if "kernel_size" in ds.attrs:
            kernel_size = ds.attrs["kernel_size"]
        else:
            kernel_size = 5
        print(
            "%s: Trimming using %d-point median filter diff of %f pct"
            % (var, kernel_size, ds.attrs[var + "_med_diff_pct"])
        )
        filtered = scipy.signal.medfilt(ds[var], kernel_size=kernel_size)
        bads = (
            100 * np.abs(ds[var] - filtered) / ds[var] > ds.attrs[var + "_med_diff_pct"]
        )
        ds[var][bads] = np.nan

        notetxt = (
            "Values filled where percent difference between "
            "%d-point median filter and original values is greater "
            "than %f. " % (kernel_size, ds.attrs[var + "_med_diff_pct"])
        )

        ds = utils.insert_note(ds, var, notetxt)

    return ds


def trim_bad_ens(ds, var):
    if var + "_bad_ens" in ds.attrs:
        inc = np.arange(0, len(ds.attrs[var + "_bad_ens"]), 2)
        for n in inc:
            print(
                "%s: Trimming using bad_ens %s"
                % (var, str(ds.attrs[var + "_bad_ens"][n : n + 2]))
            )
            if isinstance(ds.attrs[var + "_bad_ens"][n], str):
                bads = (ds["time"] >= np.datetime64(ds.attrs[var + "_bad_ens"][n])) & (
                    ds["time"] <= np.datetime64(ds.attrs[var + "_bad_ens"][n + 1])
                )
                ds[var] = ds[var].where(~bads)
            else:
                bads = np.full(ds[var].shape, False)
                bads[
                    np.arange(
                        ds.attrs[var + "_bad_ens"][n], ds.attrs[var + "_bad_ens"][n + 1]
                    )
                ] = True
                ds[var][bads] = np.nan

            notetxt = "Data clipped using bad_ens values of %s. " % (
                str(ds.attrs[var + "_bad_ens"])
            )

            ds = utils.insert_note(ds, var, notetxt)

    return ds


def trim_by_salinity(ds, var):
    if (
        "trim_by_salinity" in ds.attrs
        and ds.attrs["trim_by_salinity"].lower() == "true"
        and var in ds
    ):  # xarray doesn't support writing attributes as booleans
        if (
            "trim_by_salinity_exclude" in ds.attrs
            and var in ds.attrs["trim_by_salinity_exclude"]
        ):
            pass
        else:
            print("%s: Trimming using valid salinity threshold" % var)
            ds[var][ds["S_41"].isnull()] = np.nan

            if var != "S_41":
                notetxt = "Values filled using valid salinity threshold. "

                ds = utils.insert_note(ds, var, notetxt)

    return ds


def trim_by_any(ds, var):
    attrlist = []
    for a in ds.attrs:
        if "trim_by" in a:
            attrlist.append(a)

    for a in attrlist:
        if (
            a in ds.attrs and ds.attrs[a].lower() == "true" and var in ds
        ):  # xarray doesn't support writing attributes as booleans
            if f"{a}_exclude" in ds.attrs and var in ds.attrs[f"{a}_exclude"]:
                pass
            else:
                trimvar = a.split("trim_by_")[-1]
                print(f"{var}: Trimming using valid {trimvar} threshold")
                ds[var][ds[trimvar].isnull()] = np.nan

                if var != trimvar:
                    notetxt = f"Values filled using valid {trimvar} threshold. "

                    ds = utils.insert_note(ds, var, notetxt)

    return ds


def trim_max_std(ds, var):
    if var + "_std_max" in ds.attrs:
        print(
            "%s: Trimming using maximum standard deviation of %f"
            % (var, ds.attrs[var + "_std_max"])
        )
        ds[var][ds["Turb_std"] > ds.attrs[var + "_std_max"]] = np.nan

        notetxt = (
            "Values filled where standard deviation greater than %f "
            "units. " % ds.attrs[var + "_std_max"]
        )

        ds = utils.insert_note(ds, var, notetxt)

    return ds