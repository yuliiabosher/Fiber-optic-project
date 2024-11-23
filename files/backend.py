import os
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import string
import folium
import folium.plugins
from typing import Optional, Union
import boto3
from datetime import datetime
import numpy as np
from branca.colormap import linear
import os.path
import glob
import errno
from functools import partial
import seaborn as sns
import matplotlib.pyplot as plt
import io
import base64
from time import sleep
import csv

#########################
#                      Backend                              #
#########################
class Backend:
    def __init__(self):
        # Short on memory, so lets load everything here so that it is only loaded once, at runtime
        # This will allow the for the page to load quicker too
        self.choropleth_data = []
        for n, year in enumerate(range(2018, 2025)):
            self.choropleth_data.append(
                self.get_choropleth_for_full_fibre_availability(year, n)
            )
            sleep(1)
        
        data_dir = "files/data/"
        files = dict(
            postcode=(
                "%s/ONSPD_FEB_2024_UK/Data/ONSPD_FEB_2024_UK.csv" % data_dir,
                partial(lambda file: pd.read_csv(file, quoting=csv.QUOTE_NONE)),
            ),
            postcode_broadband=(
                "%s/202401_fixed_postcode_coverage_r01/postcode_files" % data_dir,
                lambda dir: pd.concat(
                    [pd.read_csv(os.path.join(dir, f)) for f in os.listdir(dir)],
                    ignore_index=True,
                    quoting=csv.QUOTE_NONE
                ),
            ),
            pcon_broadband=(
                "%s/202401_fixed_pcon_coverage_r01/202401_fixed_pcon_coverage_r01.csv"
                % data_dir,
                partial(
                    lambda file: pd.read_csv(file,quoting=csv.QUOTE_NONE, encoding="latin-1")
                ),
            ),
            census_population=(
                "%s/2011_census_output_areas" % data_dir,
                lambda dir: pd.concat(
                    [pd.read_csv(os.path.join(dir, f)) for f in os.listdir(dir)],
                    ignore_index=True,
                    quoting=csv.QUOTE_NONE
                ),
            ),
        )
        

        dfs = {}
        for filename, values in files.items():
            path, func = values
            self.check_filepath(path)
            dfs["df_%s" % filename] = func(path)
        dfs = self.prepare_data(**dfs)
        df_merged_ONS_OFCOM = self.merge_ons_ofcom(dfs)
        df_combined_ONS_OFCOM = self.create_estimate_df_for_area_type(
            df_merged_ONS_OFCOM
        )
        del dfs

        df_unable_to_get_broadband = (
            self.create_df_for_those_unable_to_recieve_broadband(df_combined_ONS_OFCOM)
        )

        self.graphs = []
        self.graphs.append(
            self.create_graph__for_mean_percentage_of_those_unable_to_get_broadband(
                df_unable_to_get_broadband
            )
        )
        self.graphs.append(
            self.create_graph_for_mbit_download_speed(df_combined_ONS_OFCOM)
        )
        self.graphs.append(self.create_graph_for_fast_broadband(df_combined_ONS_OFCOM))
        self.graphs.append(
            self.create_graph_for_percentage_by_access_to_full_fibre(
                df_combined_ONS_OFCOM
            )
        )
    

    def get_constituencies(self) -> gpd.geodataframe.GeoDataFrame:
        constituencies = gpd.read_file(
            "files/data/Westminster_Parliamentary_Constituencies_Dec_2021_UK_BUC_2022_-8882165546947265805.zip"
        )
        constituencies["PCON21NM"] = constituencies["PCON21NM"].str.upper().str.strip()
        return constituencies[["PCON21CD", "PCON21NM", "geometry"]]

    def get_ofcom_full_fibre(self, file: str) -> pd.core.frame.DataFrame:
        ofcom_df = pd.read_csv(file, quoting=csv.QUOTE_NONE,encoding="latin")
        ofcom_df.rename(
            columns={
                "parl_const_name": "parliamentary_constituency_name",
                "FTTP availability (Count premises)": "Number of premises with Full Fibre availability",
            },
            inplace=True,
        )
        ofcom_full_fibre_df = ofcom_df[
            [
                "parliamentary_constituency_name",
                "All Premises",
                "Number of premises with Full Fibre availability",
            ]
        ]
        if (
            ofcom_full_fibre_df["parliamentary_constituency_name"]
            .str.contains("YNYS MÃN")
            .any()
        ):
            index = ofcom_full_fibre_df[
                ofcom_full_fibre_df["parliamentary_constituency_name"].str.contains(
                    "YNYS MÃN"
                )
            ].index[0]
            ofcom_full_fibre_df.loc[index, "parliamentary_constituency_name"] = (
                "YNYS MÔN"
            )
        ofcom_full_fibre_df["parliamentary_constituency_name"] = (
            ofcom_full_fibre_df["parliamentary_constituency_name"]
            .str.upper()
            .str.strip()
        )
        return ofcom_full_fibre_df

    def merge_ofcom_with_constituencies(
        self,
        ofcom: pd.core.frame.DataFrame,
        constituencies: gpd.geodataframe.GeoDataFrame,
    ):
        fibre_by_constituency_geo_df = constituencies.merge(
            ofcom, left_on="PCON21NM", right_on="parliamentary_constituency_name"
        )
        fibre_by_constituency_geo_df.drop("PCON21NM", axis=1, inplace=True)
        fibre_by_constituency_geo_df.columns = [
            "Constituency Code",
            "geometry",
            "Constituency Name",
            "Total Premises",
            "Premises with Full Fibre Availability",
        ]
        fibre_by_constituency_geo_df[
            "Percentage of Premises with Full Fibre Availability"
        ] = (
            fibre_by_constituency_geo_df["Premises with Full Fibre Availability"]
            / fibre_by_constituency_geo_df["Total Premises"]
        )
        return fibre_by_constituency_geo_df

    def make_choropleth(
        self,
        df: pd.core.frame.DataFrame,
        column: str,
        title: str,
        year: int,
        del_color_scale: bool,
    ) -> folium.Choropleth:
        choropleth = folium.Choropleth(
            geo_data=df,
            data=df[column],
            columns=[column],
            key_on="feature.id",
            nan_fill_color="purple",
            fill_opacity=0.3,
            line_opacity=0.1,
            legend_name=title,
            name=f"%s (%s)" % (title, year),
        )
        setattr(choropleth.color_scale, "text_color", "red")
        if del_color_scale:
            for child in choropleth._children:
                if child.startswith("color_map"):
                    del choropleth._children[child]
        return choropleth

    def get_choropleth_for_full_fibre_availability(
        self, year: int, del_color_scale: bool = False
    ) -> Optional[folium.Choropleth]:
        constituencies = self.get_constituencies()
        link = "https://raw.githubusercontent.com/yuliiabosher/Fiber-optic-project/refs/heads/parliamentary-constituencies"
        filename = string.Template("${year}${n}_fixed_pcon_coverage_r${r}.csv")
        files = {
            2018: filename.substitute(year=2018, n="09", r="01"),
            2019: filename.substitute(year=2019, n="09", r="01"),
            2020: filename.substitute(year=2020, n="09", r="01"),
            2021: filename.substitute(year=2021, n="09", r="01"),
            2022: filename.substitute(year=2022, n="09", r="02"),
            2024: filename.substitute(year=2024, n="01", r="01"),
        }
        if year not in files:
            return None
        link_to_file = os.path.join(link, files[year])
        ofcom = self.get_ofcom_full_fibre(link_to_file)
        fibre_by_constituency_geo_df = self.merge_ofcom_with_constituencies(
            ofcom, constituencies
        )
        choropleth = self.make_choropleth(
            fibre_by_constituency_geo_df,
            "Percentage of Premises with Full Fibre Availability",
            "Full Fibre Availability",
            year,
            del_color_scale,
        )
        return choropleth, fibre_by_constituency_geo_df

    def get_choropleth_for_full_fibre_availability_with_slider(
        self, choropleth_data
    ) -> Optional[folium.plugins.TimeSliderChoropleth]:
        dfs = []
        years = [2018, 2019, 2020, 2021, 2022, 2024]
        for n, year in enumerate(years):
            if choropleth_data[n]:
                df = choropleth_data[n][1]
                df["year"] = [
                    int(datetime(year, 1, 1).timestamp()) for i in range(df.shape[0])
                ]
                # append df to list of dfs
                dfs.append(df)

        merged = gpd.GeoDataFrame(data=pd.concat(dfs))
        # get min , max value of full fibre availability percentage
        min_color = merged["Percentage of Premises with Full Fibre Availability"].min()
        max_color = merged["Percentage of Premises with Full Fibre Availability"].max()

        # Create a color scale from the min and max of the values
        cmap = linear.PuRd_09.scale(min_color, max_color)
        merged["opacity"] = [0.5 for i in range(merged.shape[0])]
        merged["color"] = merged[
            "Percentage of Premises with Full Fibre Availability"
        ].apply(cmap)

        # Get unique set of geometries, with constituency as the index
        gdf = merged.drop_duplicates("Constituency Code")[
            ["Constituency Code", "geometry"]
        ]
        gdf.set_index("Constituency Code", drop=True, inplace=True)

        # group by constiuency
        grouped_by = merged.groupby("Constituency Code")

        # make a style dict with datetime, opacity and color for each entry in the group, indexed by constituency
        styledata = dict()
        for constituency in gdf.index:
            group = grouped_by.get_group(constituency)
            group = group[["year", "opacity", "color"]]
            group.set_index("year", drop=True, inplace=True)
            styledata[constituency] = group

        # Use a dict comprehension to turn the dfs into dictionaries, maintaining the original key
        styledict = {
            constituency: data.to_dict(orient="index")
            for constituency, data in styledata.items()
        }
        choropleth_with_slider = folium.plugins.TimeSliderChoropleth(
            data=gdf, styledict=styledict
        )
        return choropleth_with_slider

    def check_filepath(self, file: str) -> bool:
        if not os.path.exists(file):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file)
        return True

    def prepare_data(
        self,
        df_postcode: pd.core.frame.DataFrame,
        df_postcode_broadband: pd.core.frame.DataFrame,
        df_pcon_broadband: pd.core.frame.DataFrame,
        df_census_population: pd.core.frame.DataFrame,
    ) -> dict:

        dfs = dict()
        # - Select relevant columns for analysis
        # These columns look useful, based on the ONSßPD Record Specification documented in the ONSPD User Guide
        ons_postcode_data_columns = [
            "pcds",
            "pcon",
            "doterm",
            "ctry",
            "ur01ind",
            "lat",
            "long",
            "oa11",
        ]
        df_ONS_postcode = df_postcode[ons_postcode_data_columns]

        # - Remove  postcodes that are not live
        # Rows where doterm is null are live postcodes: after that we can drop the doterm column as it's not useful to us
        df_live_ONS_postcode = df_ONS_postcode.loc[df_ONS_postcode["doterm"].isnull()]
        df_live_ONS_postcode = df_live_ONS_postcode.drop("doterm", axis=1)

        # - Remove postcodes that are not associated with a parliamentary constituency
        dfs["df_live_ONS_postcode_pcon"] = df_live_ONS_postcode.loc[
            df_live_ONS_postcode["pcon"].notnull()
        ]

        ofcom_postcode_data_columns = [
            "postcode_space",
            "% of premises with 30<300Mbit/s download speed",
            "% of premises with >=300Mbit/s download speed",
            "% of premises with 0<2Mbit/s download speed",
            "% of premises with 2<5Mbit/s download speed",
            "% of premises with 5<10Mbit/s download speed",
            "% of premises with 10<30Mbit/s download speed",
            "SFBB availability (% premises)",
            "UFBB (100Mbit/s) availability (% premises)",
            "UFBB availability (% premises)",
            "% of premises unable to receive 2Mbit/s",
            "% of premises unable to receive 5Mbit/s",
            "% of premises unable to receive 10Mbit/s",
            "% of premises unable to receive 30Mbit/s",
            "Gigabit availability (% premises)",
        ]
        df_OFCOM_postcode_broadband = df_postcode_broadband[ofcom_postcode_data_columns]
        # - Rename the postcode column to align with ONS postcode data column name
        dfs["df_OFCOM_postcode_broadband"] = df_OFCOM_postcode_broadband.rename(
            columns={"postcode_space": "pcds"}
        )

        # - Select relevant columns for analysis
        ofcom_pcon_columns = [
            "parl_const",
            "Full Fibre availability (% premises)",
            "Gigabit availability (% premises)",
        ]
        df_OFCOM_pcon = df_pcon_broadband[ofcom_pcon_columns]

        # - Rename columns to align with ONS data and prevent clashes with OFCOM postcode data
        dfs["df_OFCOM_pcon"] = df_OFCOM_pcon.rename(
            columns={
                "parl_const": "pcon",
                "Full Fibre availability (% premises)": "PCON Full Fibre availability (% premises)",
                "Gigabit availability (% premises)": "PCON Gigabit availability (% premises)",
            }
        )

        ons_OA_population_columns = [
            "geography code",
            "Area/Population Density: All usual residents; measures: Value",
        ]
        df_OA_population = df_census_population[ons_OA_population_columns]

        # - Rename columns to align with ONS data and prevent clashes with OFCOM postcode data
        dfs["df_OA_population"] = df_OA_population.rename(
            columns={
                "geography code": "oa11",
                "Area/Population Density: All usual residents; measures: Value": "oa11 Usual Resident Population Count",
            }
        )
        return dfs

    def merge_ons_ofcom(self, dfs: dict) -> pd.core.frame.DataFrame:
        df_merged_ONS_OFCOM = pd.merge(
            dfs["df_live_ONS_postcode_pcon"],
            dfs["df_OFCOM_pcon"],
            on=["pcon"],
            how="inner",
        )

        # - Merge in OFCOM postcode data
        df_merged_ONS_OFCOM = pd.merge(
            df_merged_ONS_OFCOM,
            dfs["df_OFCOM_postcode_broadband"],
            on=["pcds"],
            how="inner",
        )

        # - Merge in OA population data
        return pd.merge(
            df_merged_ONS_OFCOM, dfs["df_OA_population"], on=["oa11"], how="inner"
        )

    def estimate_population_per_postocde_availability(
        self, row: pd.core.series.Series
    ) -> float:
        return row["oa11 Usual Resident Population Count"] / row["count"]

    def estimate_fullfibre_availability(self, row: pd.core.series.Series) -> float:
        return (
            row["PCON Full Fibre availability (% premises)"]
            / row["PCON Gigabit availability (% premises)"]
            * row["Gigabit availability (% premises)"]
        )

    def estimate_poulation_fullfibre_availability(
        self, row: pd.core.series.Series
    ) -> float:
        return (
            row["Estimated Full Fibre availability (% premises)"]
            / 100
            * row["Estimated Usual Resident Population"]
        )

    def classify_urban_rural(self, row: pd.core.series.Series) -> Optional[str]:
        if (
            row["ctry"] == "E92000001"
            or row["ctry"] == "W92000004"
            or row["ctry"] == "S92000003"
        ):
            if int(row["ur01ind"]) >= 6:
                return "Rural"
            else:
                return "Urban"

        if row["ctry"] == "N92000002":
            if row["ur01ind"] == "F" or row["ur01ind"] == "G" or row["ur01ind"] == "H":
                return "Rural"
            else:
                return "Urban"

        if row["ctry"] == "L93000001" or row["ctry"] == "M83000003":
            return "Rural"

        return None

    def create_estimate_df_for_area_type(
        self, df_merged_ONS_OFCOM: pd.core.frame.DataFrame
    ) -> pd.core.frame.DataFrame:
        # - Create a dataframe that counts the number of postcodes in each Census 2011 output area
        df_apportioned_population_in_OA = df_merged_ONS_OFCOM.groupby("oa11")[
            ["oa11 Usual Resident Population Count"]
        ].value_counts()
        df_apportioned_population_in_OA = (
            df_apportioned_population_in_OA.to_frame().reset_index()
        )

        # - Apply the custom function create a new column "Estimated Usual Resident Population" and drop other unrequired columns
        df_apportioned_population_in_OA["Estimated Usual Resident Population"] = (
            df_apportioned_population_in_OA.apply(
                self.estimate_population_per_postocde_availability, axis=1
            )
        )
        df_apportioned_population_in_OA = df_apportioned_population_in_OA.drop(
            columns=["count", "oa11 Usual Resident Population Count"]
        )

        # - Merge in to existing data
        df_merged_ONS_OFCOM_with_population = pd.merge(
            df_merged_ONS_OFCOM,
            df_apportioned_population_in_OA,
            on=["oa11"],
            how="inner",
        )

        df_merged_ONS_OFCOM_with_estimate = df_merged_ONS_OFCOM_with_population.copy()
        df_merged_ONS_OFCOM_with_estimate[
            "Estimated Full Fibre availability (% premises)"
        ] = df_merged_ONS_OFCOM_with_estimate.apply(
            self.estimate_fullfibre_availability, axis=1
        )

        # Apply the custom function create a new column "Estimated Full Fibre Availability (% premesis)
        df_merged_ONS_OFCOM_with_estimate[
            "Estimated Full Fibre availability (population)"
        ] = df_merged_ONS_OFCOM_with_estimate.apply(
            self.estimate_poulation_fullfibre_availability, axis=1
        )

        # Apply the custom function create a new column "Urban/Rural"
        df_combined_ONS_OFCOM = df_merged_ONS_OFCOM_with_estimate.copy()
        df_combined_ONS_OFCOM["Urban/Rural"] = df_combined_ONS_OFCOM.apply(
            self.classify_urban_rural, axis=1
        )

        return df_combined_ONS_OFCOM

    def create_graph_image(self, fig: plt.figure) -> str:
        # create a variable to hold data in memory as bytes
        imgdata = io.BytesIO()
        # save the figure as a png in the  bytes object
        fig.savefig(imgdata, format="png")

        # encode the imgdata to base64 and decode it using utf-8
        encoded = base64.b64encode(imgdata.getvalue()).decode("utf-8")

        # write the html code and write it out
        return "<img src='data:image/png;base64,{}'>".format(encoded)

    def create_df_for_those_unable_to_recieve_broadband(
        self, df_combined_ONS_OFCOM: pd.core.frame.DataFrame
    ) -> pd.core.frame.DataFrame:
        colums_unable_to_receive = [
            "% of premises unable to receive 2Mbit/s",
            "% of premises unable to receive 5Mbit/s",
            "% of premises unable to receive 10Mbit/s",
            "% of premises unable to receive 30Mbit/s",
            "Urban/Rural",
        ]
        df_unable_to_receive_broadband = df_combined_ONS_OFCOM[colums_unable_to_receive]
        df_mean_unable_to_receive_broadband = df_unable_to_receive_broadband.groupby(
            ["Urban/Rural"]
        ).mean()
        df_mean_unable_to_receive_broadband["Urban/Rural"] = ["Rural", "Urban"]

        return df_mean_unable_to_receive_broadband.melt(
            id_vars=["Urban/Rural"], value_vars=colums_unable_to_receive
        )

    def create_graph__for_mean_percentage_of_those_unable_to_get_broadband(
        self, melted: pd.core.frame.DataFrame
    ) -> str:
        fig, ax = plt.subplots(figsize=(5, 5))
        sns.barplot(
            melted,
            x="variable",
            y="value",
            hue="Urban/Rural",
            palette=sns.color_palette("mako", 2),
            ax=ax,
        )
        sns.barplot().set_title(
            "Mean Percentage of Urban/Rural premesis unable to receive various broadband speeds"
        )

        ax.tick_params(axis="x", labelrotation=45)
        ax.set_xticks(
            ticks=ax.get_xticks(), labels=ax.get_xticklabels(), rotation=45, ha="right"
        )

        return self.create_graph_image(fig)

    def create_graph_for_mbit_download_speed(
        self, df_combined_ONS_OFCOM: pd.core.frame.DataFrame
    ) -> str:
        fig, ax = plt.subplots(figsize=(5, 5))

        columns_mbits_supported = [
            "% of premises with 0<2Mbit/s download speed",
            "% of premises with 2<5Mbit/s download speed",
            "% of premises with 5<10Mbit/s download speed",
            "% of premises with 10<30Mbit/s download speed",
            "% of premises with 30<300Mbit/s download speed",
            "% of premises with >=300Mbit/s download speed",
            "Urban/Rural",
        ]

        df_mbit_download_speed = df_combined_ONS_OFCOM[columns_mbits_supported]
        df_mean_mbit_download_speed = df_mbit_download_speed.groupby(
            ["Urban/Rural"]
        ).mean()
        colors = sns.color_palette("mako")[0:6]
        df_mean_mbit_download_speed.plot(kind="bar", stacked=True, color=colors, ax=ax)

        plt.title(
            "Mean Percentage of Urban and Rural Premesis with different download speeds"
        )
        plt.ylabel("Percentage")
        plt.legend(bbox_to_anchor=(1.05, 1.0), loc="upper left")
        return self.create_graph_image(fig)

    def create_graph_for_fast_broadband(
        self, df_combined_ONS_OFCOM: pd.core.frame.DataFrame
    ) -> str:
        columns_fast_broadband = [
            "SFBB availability (% premises)",
            "UFBB (100Mbit/s) availability (% premises)",
            "UFBB availability (% premises)",
            "Gigabit availability (% premises)",
            "Estimated Full Fibre availability (% premises)",
            "Urban/Rural",
        ]

        df_fast_broadband = df_combined_ONS_OFCOM[columns_fast_broadband]
        df_mean_fast_broadband = df_fast_broadband.groupby(["Urban/Rural"]).mean()
        df_mean_fast_broadband["Urban/Rural"] = ["Rural", "Urban"]
        melted = df_mean_fast_broadband.melt(
            id_vars=["Urban/Rural"], value_vars=columns_fast_broadband
        )

        fig, ax = plt.subplots(figsize=(5, 5))
        sns.barplot(
            melted,
            x="variable",
            y="value",
            hue="Urban/Rural",
            palette=sns.color_palette("mako", 2),
            ax=ax,
        )
        sns.barplot().set_title(
            "Mean Percentage of Urban/Rural premesis with different types of broadband available"
        )
        ax.tick_params(axis="x", labelrotation=45)
        ax.set_xticks(
            ticks=ax.get_xticks(), labels=ax.get_xticklabels(), rotation=45, ha="right"
        )
        return self.create_graph_image(fig)

    def create_graph_for_percentage_by_access_to_full_fibre(
        self, df_combined_ONS_OFCOM: pd.core.frame.DataFrame
    ) -> str:
        total_population = df_combined_ONS_OFCOM[
            "Estimated Usual Resident Population"
        ].sum()

        total_population_urban = df_combined_ONS_OFCOM[
            df_combined_ONS_OFCOM["Urban/Rural"] == "Urban"
        ]["Estimated Usual Resident Population"].sum()

        total_population_rural = df_combined_ONS_OFCOM[
            df_combined_ONS_OFCOM["Urban/Rural"] == "Rural"
        ]["Estimated Usual Resident Population"].sum()

        columns_full_fibre_broadband = [
            "pcds",
            "ctry",
            "Estimated Usual Resident Population",
            "Estimated Full Fibre availability (% premises)",
            "Urban/Rural",
        ]
        df_full_fibre_broadband = df_combined_ONS_OFCOM[columns_full_fibre_broadband]
        df_full_fibre_broadband["Population with no Full Fibre"] = (
            df_full_fibre_broadband["Estimated Usual Resident Population"]
            * df_full_fibre_broadband["Estimated Full Fibre availability (% premises)"]
        )

        population_no_fibre = df_full_fibre_broadband[
            "Population with no Full Fibre"
        ].sum()
        population_no_fibre_urban = df_full_fibre_broadband[
            df_full_fibre_broadband["Urban/Rural"] == "Urban"
        ]["Population with no Full Fibre"].sum()
        population_no_fibre_rural = df_full_fibre_broadband[
            df_full_fibre_broadband["Urban/Rural"] == "Rural"
        ]["Population with no Full Fibre"].sum()

        # Calculate the percentage of the population with no full fibre availability (estimated)
        percentage_population_no_fibre = population_no_fibre / total_population * 100
        percentage_rural_population_no_fibre = (
            population_no_fibre_rural / total_population_rural * 100
        )
        percentage_urban_population_no_fibre = (
            population_no_fibre_urban / total_population_urban * 100
        )

        df_percentage_pop_with_access_to_full_fibre = {
            "No Full Fibre": [
                percentage_population_no_fibre,
                percentage_rural_population_no_fibre,
                percentage_urban_population_no_fibre,
            ],
            "Full Fibre": [
                100 - percentage_population_no_fibre,
                100 - percentage_rural_population_no_fibre,
                100 - percentage_urban_population_no_fibre,
            ],
            "Population Type": ["Total", "Rural", "Urban"],
        }
        df_percentage_pop_with_access_to_full_fibre = pd.DataFrame(
            df_percentage_pop_with_access_to_full_fibre
        )
        df_percentage_pop_with_access_to_full_fibre = (
            df_percentage_pop_with_access_to_full_fibre.set_index("Population Type")
        )

        fig, ax = plt.subplots(figsize=(5, 5))

        colors = sns.color_palette("mako")[2:4]
        df_percentage_pop_with_access_to_full_fibre.plot(
            kind="bar", stacked=True, color=colors, ax=ax
        )

        # Add Title and Labels, and move the legend to the side
        plt.title("Percentage of Population with access to Full Fibre")
        plt.ylabel("Percentage")
        plt.legend(bbox_to_anchor=(1.05, 1.0), loc="upper left")
        return self.create_graph_image(fig)
