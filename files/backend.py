import os
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import string
import folium
import folium.plugins
from typing import Optional, Union, Tuple
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
        eu_broadband_df = self.get_europe_broadband_data()
        eu_shp_gdf = self.load_europe_shapefile()
        self.eu_broadband_geo = self.prepare_eu_gdf(eu_broadband_df, eu_shp_gdf)
        self.eu_choropleth = self.get_choropleth_for_eu_broadband_with_slider(
            self.eu_broadband_geo, "Percentage of households with FTTP availability"
        )

        eu_broadband_predictions_df = self.eu_broadband_predictions(
            include_current=False
        )
        eu_broadband_predictions_geo = self.prepare_eu_gdf(
            eu_broadband_predictions_df, eu_shp_gdf
        )
        self.eu_choropleth_predictions = (
            self.get_choropleth_for_eu_broadband_with_slider(
                eu_broadband_predictions_geo, "FTTP", colormap=linear.PuRd_09
            )
        )
        # Short on memory, so lets load everything here so that it is only loaded once, at runtime
        # This will allow the for the page to load quicker too
        # TODO: move maps to top of app.py to prevent from needing to reload
        self.choropleth_data = []
        for n, year in enumerate(range(2018, 2025)):
            self.choropleth_data.append(
                self.get_choropleth_for_full_fibre_availability(year, n)
            )

        """data_dir = "files/data/"
        files = dict(
            postcode=(
                "%s/ONSPD_FEB_2024_UK/Data/ONSPD_FEB_2024_UK.csv" % data_dir,
                partial(lambda file: pd.read_csv(file)),
            ),
            postcode_broadband=(
                "%s/202401_fixed_postcode_coverage_r01/postcode_files" % data_dir,
                lambda dir: pd.concat(
                    [pd.read_csv(os.path.join(dir, f)) for f in os.listdir(dir)],
                    ignore_index=True,
                ),
            ),
            pcon_broadband=(
                "%s/202401_fixed_pcon_coverage_r01/202401_fixed_pcon_coverage_r01.csv"
                % data_dir,
                partial(
                    lambda file: pd.read_csv(file, encoding="latin-1")
                ),
            ),
            census_population=(
                "%s/2011_census_output_areas" % data_dir,
                lambda dir: pd.concat(
                    [pd.read_csv(os.path.join(dir, f)) for f in os.listdir(dir)],
                    ignore_index=True,
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
        """
        self.RUC_classifications = self.get_rural_urban_classifications()
        self.constituencies_with_RUC = self.get_constituencies_2022_with_RUC()

    def clean_and_load_parldf(self, link_to_file: str) -> pd.core.frame.DataFrame:
        ofcom_df = pd.read_csv(link_to_file, encoding="latin")
        ofcom_full_fibre_df = ofcom_df[
            ["parliamentary_constituency_name", "Full Fibre availability (% premises)"]
        ]
        if (
            ofcom_full_fibre_df["parliamentary_constituency_name"]
            .str.contains("YNYS MÃ”N")
            .any()
        ):
            index = ofcom_full_fibre_df[
                ofcom_full_fibre_df["parliamentary_constituency_name"].str.contains(
                    "YNYS MÃ”N"
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

    def load_ofcom_from_link(self, year: int) -> Optional[pd.core.frame.DataFrame]:
        link = "https://raw.githubusercontent.com/yuliiabosher/Fiber-optic-project/refs/heads/parliamentary-constituencies"
        filename = string.Template("${year}${n}_fixed_pcon_coverage_r${r}.csv")
        files = {
            2019: filename.substitute(year=2019, n="09", r="01"),
            2020: filename.substitute(year=2020, n="09", r="01"),
            2021: filename.substitute(year=2021, n="09", r="01"),
            2022: filename.substitute(year=2022, n="09", r="02"),
            2023: filename.substitute(year=2024, n="01", r="01"),
        }
        if year not in files:
            return None
        link_to_file = os.path.join(link, files[year])
        return self.clean_and_load_parldf(link_to_file)

    def eu_broadband_predictions(
        self, include_current=False
    ) -> pd.core.frame.DataFrame:
        fileEuropeData = "files/data/EUROPE_FIBRE.csv"

        dfEuropeClean = self.prepare_df(fileEuropeData, "%")

        cols = ["Country", "Metric", "URClass"]
        dfEuropeCleanFTTP = dfEuropeClean.query('Metric == "FTTP"')

        df_final_total = self.fn_calc(
            dfEuropeCleanFTTP, "Total", string.Template("${year}%")
        )

        for year in range(2024, 2031):
            df_final_total[f"FTTP{year}"].replace(np.nan, 0, inplace=True)

        column_catalogue = {"FTTP%s" % year: str(year) for year in range(2024, 2031)}
        extra_cols = {f"{year}%": str(year) for year in range(2018, 2024)}

        if include_current:
            column_catalogue.update(extra_cols)

        df = self.fn_change_col_name(
            df_final_total[["Country", "Metric"] + list(column_catalogue.keys())].query(
                "Metric=='FTTP' & `Country` != 'EU27' & `Country` != 'EU28' & `Country` != 'Czechia'"
            ),
            column_catalogue,
        )
        eu_broadband_fttp_melted = df.melt(
            id_vars=["Country", "Metric"], var_name="Year", value_name="FTTP"
        )
        eu_broadband_fttp_pivot = eu_broadband_fttp_melted.pivot(
            index=["Country", "Year"], columns="Metric", values="FTTP"
        )
        eu_broadband_fttp_pivot.reset_index(inplace=True)
        eu_broadband_fttp_pivot.rename_axis(columns=None, inplace=True)
        eu_broadband_fttp_pivot["Year"] = eu_broadband_fttp_pivot.Year.astype(int)
        return eu_broadband_fttp_pivot

    def fn_predict_five_year(self, yearly_values: list) -> Tuple[int]:
        year = np.arange(1, 6)
        value = np.array(yearly_values)
        beta1, beta0 = np.polyfit(year, value, 1)
        return beta0, beta1

    def fn_clean_years(
        self, thisdf: pd.core.frame.DataFrame, columns: list
    ) -> pd.core.frame.DataFrame:
        for column in thisdf.columns:
            if column in columns:
                replacement_dict = {"-": "", "%": "", ",": "", " ": ""}
                for character, replacement in replacement_dict.items():
                    thisdf[column] = thisdf[column].str.replace(character, replacement)
                thisdf[column] = thisdf[column].replace("", None)
                thisdf[column] = thisdf[column].astype(float)
        return thisdf

    def fn_change_col_name(
        self, thisdf: pd.core.frame.DataFrame, name_catalogue: dict
    ) -> pd.core.frame.DataFrame:
        for oldname, newname in name_catalogue.items():
            thisdf.rename(columns={oldname: newname}, inplace=True)
        return thisdf

    def prepare_df(self, file: str, suffix: str) -> pd.core.frame.DataFrame:
        df = pd.read_csv(file)

        columns = {str(n): f"{n}{suffix}" for n in range(2018, 2024)}
        dfClean = self.fn_clean_years(df, columns.keys())

        columns.update({"Geography level": "URClass"})
        dfClean = self.fn_change_col_name(dfClean, columns)

        columns = ["Country", "Metric", "Unit"] + list(columns.values())
        dfClean = dfClean[columns]
        return dfClean

    def load_ofcom_pcodes(self):
        linktofile = "https://raw.githubusercontent.com/yuliiabosher/Fiber-optic-project/refs/heads/parliamentary-constituencies/202401_fixed_pcon_coverage_r01.csv"
        ofcom_df = pd.read_csv(linktofile, encoding="latin")
        ofcom_pc_codes_df = ofcom_df[["parliamentary_constituency_name", "parl_const"]]
        return ofcom_pc_codes_df

    def fn_calc(
        self,
        df_final: pd.core.frame.DataFrame,
        urclass: Optional[str],
        row_template: str,
    ) -> pd.core.frame.DataFrame:
        if urclass:
            df_final = df_final.query('URClass == "' + urclass + '"')
        catalogue_of_values = {year: [] for year in range(2024, 2031)}
        first_year = 2019
        for _, row in df_final.iterrows():
            rows = [
                row[row_template.substitute(year=year)] for year in range(2019, 2024)
            ]
            beta0, beta1 = self.fn_predict_five_year(rows)
            for year in catalogue_of_values.keys():
                x_year = year - first_year
                catalogue_of_values[year].append(beta0 + beta1 * x_year)

        for year, values in catalogue_of_values.items():
            df_final["FTTP%s" % year] = values
            df_final["FTTP%s" % year] = df_final["FTTP%s" % year].astype(float)
        return df_final

    def get_choropleth_for_uk_broadband_with_slider(
        self, choropleth_data, colname, colormap=linear.YlOrRd_06
    ) -> Optional[folium.plugins.TimeSliderChoropleth]:
        choropleth_data["year"] = [
            int(datetime(year, 1, 1).timestamp())
            for year in choropleth_data.index.values
        ]

        min_color = choropleth_data[colname].min()
        max_color = choropleth_data[colname].max()

        cmap = colormap.scale(min_color, max_color)
        choropleth_data["opacity"] = [0.5 for i in range(choropleth_data.shape[0])]
        choropleth_data["color"] = choropleth_data[colname].apply(cmap)

        gdf = choropleth_data.drop_duplicates("PCON21CD")[["PCON21CD", "geometry"]]

        gdf.set_index("PCON21CD", drop=True, inplace=True)
        grouped_by = choropleth_data.groupby("PCON21CD")

        styledata = dict()
        for country in gdf.index:
            group = grouped_by.get_group(country)
            group = group[["year", "opacity", "color"]]
            group.set_index("year", drop=True, inplace=True)
            styledata[country] = group

        styledict = {
            country: data.to_dict(orient="index") for country, data in styledata.items()
        }

        choropleth_with_slider = folium.plugins.TimeSliderChoropleth(
            data=gdf, styledict=styledict, date_options="YYYY"
        )
        return choropleth_with_slider, cmap

    def get_rural_urban_classifications(self):
        fileUrbanRuralClassification = "files/data/pcon_ruc.csv"
        if os.path.exists(fileUrbanRuralClassification):
            dfRUC = pd.read_csv(fileUrbanRuralClassification)
        else:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), fileUrbanRuralClassification
            )
        return dfRUC[["gss-code", "ruc-cluster-label"]]

    def get_constituencies_2022_with_RUC(self):
        constituencies = gpd.read_file(
            "files/data/Westminster_Parliamentary_Constituencies_Dec_2021_UK_BUC_2022_-8882165546947265805.zip"
        )
        constituencies_cleaned = constituencies[["PCON21CD", "PCON21NM", "geometry"]]
        ofcom = pd.read_csv(
            "files/data/202401_fixed_pcon_coverage_r01.csv", encoding="latin"
        )
        ofcom_full_fibre = ofcom[
            [
                "parl_const",
                "parliamentary_constituency_name",
                "All Premises",
                "Number of premises with Full Fibre availability",
            ]
        ]
        fibre_by_constituency_geo = constituencies_cleaned.merge(
            ofcom_full_fibre, left_on="PCON21CD", right_on="parl_const"
        )
        fibre_by_constituency_geo = fibre_by_constituency_geo.merge(
            self.RUC_classifications, left_on="PCON21CD", right_on="gss-code"
        )
        fibre_by_constituency_geo.drop("parl_const", axis=1, inplace=True)
        fibre_by_constituency_geo.drop(
            "parliamentary_constituency_name", axis=1, inplace=True
        )
        fibre_by_constituency_geo.drop("gss-code", axis=1, inplace=True)
        fibre_by_constituency_geo.columns = [
            "Constituency Code",
            "Constituency Name",
            "geometry",
            "Total Premises",
            "Premises with Full Fibre Availability",
            "Urban/Rural Classification",
        ]
        fibre_by_constituency_geo[
            "Percentage of Premises with Full Fibre Availability"
        ] = (
            fibre_by_constituency_geo["Premises with Full Fibre Availability"]
            / fibre_by_constituency_geo["Total Premises"]
        )
        return fibre_by_constituency_geo

    def get_choropleth_for_eu_broadband_with_slider(
        self, choropleth_data, colname, colormap=linear.YlOrRd_06
    ) -> Optional[folium.plugins.TimeSliderChoropleth]:
        choropleth_data["year"] = [
            int(datetime(year, 1, 1).timestamp())
            for year in choropleth_data.index.values
        ]
        choropleth_data.loc[
            choropleth_data.loc[:]["Country"] == "United Kingdom", "Country"
        ] = "uk"

        min_color = choropleth_data[colname].min()
        max_color = choropleth_data[colname].max()

        cmap = colormap.scale(min_color, max_color)
        choropleth_data["opacity"] = [0.5 for i in range(choropleth_data.shape[0])]
        choropleth_data["color"] = choropleth_data[colname].apply(cmap)

        gdf = choropleth_data.drop_duplicates("Country")[["Country", "geometry"]]

        gdf.set_index("Country", drop=True, inplace=True)
        grouped_by = choropleth_data.groupby("Country")

        styledata = dict()
        for country in gdf.index:
            group = grouped_by.get_group(country)
            group = group[["year", "opacity", "color"]]
            group.set_index("year", drop=True, inplace=True)
            styledata[country] = group

        styledict = {
            country: data.to_dict(orient="index") for country, data in styledata.items()
        }
        choropleth_with_slider = folium.plugins.TimeSliderChoropleth(
            data=gdf, styledict=styledict, date_options="YYYY"
        )
        return choropleth_with_slider, cmap

    def check_filepath(self, file: str) -> bool:
        if not os.path.exists(file):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file)
        return True

    def prepare_eu_gdf(self, eu_broadband_df, eu_shp_gdf):
        eu_broadband_geo = eu_broadband_df.merge(
            eu_shp_gdf, left_on="Country", right_on="NAME_ENGL", how="left"
        )
        eu_broadband_geo.drop(columns=["NAME_ENGL"], inplace=True)
        eu_broadband_geo.set_index("Year", inplace=True)
        return gpd.GeoDataFrame(eu_broadband_geo, geometry="geometry")

    def load_europe_shapefile(self):
        country_polygons = gpd.read_file("files/data/CNTR_RG_01M_2024_4326.shp.zip")
        country_polygons = country_polygons[["NAME_ENGL", "geometry"]]
        return country_polygons

    def prepare_constituency_predictions(self):
        ofcom_pc_codes_df = self.load_ofcom_pcodes()
        final_df = None
        for year in range(2019, 2024):
            df = self.load_ofcom_from_link(year)
            if isinstance(df, pd.core.frame.DataFrame):
                if year == 2024:
                    # problem with 2024, it should be named 2023 but iremains incorrect
                    year -= 1
                df.rename(
                    columns={"Full Fibre availability (% premises)": "FTTP%s" % year},
                    inplace=True,
                )
                if final_df is not None:
                    final_df = final_df.merge(
                        df, on=["parliamentary_constituency_name"], how="inner"
                    )
                else:
                    final_df = df

        final_df = final_df.merge(
            ofcom_pc_codes_df, on=["parliamentary_constituency_name"], how="inner"
        )
        final_df = self.fn_calc(final_df, None, string.Template("FTTP${year}"))
        final_df.drop(["parliamentary_constituency_name"], axis=1, inplace=True)
        uk_broadband_fttp_melted = final_df.melt(
            id_vars=["parl_const"], var_name="Year", value_name="FTTP"
        )
        uk_broadband_fttp_melted.reset_index(inplace=True)
        uk_broadband_fttp_melted.rename_axis(columns=None, inplace=True)
        uk_broadband_fttp_melted["Year"] = uk_broadband_fttp_melted.Year.str.replace(
            "FTTP", ""
        ).astype(int)

        gdf = self.get_constituencies()
        fibre_by_constituency_geo = uk_broadband_fttp_melted.merge(
            gdf, right_on="PCON21CD", left_on="parl_const"
        )
        fibre_by_constituency_geo.set_index("Year", inplace=True, drop=True)
        fibre_by_constituency_geo.drop(["PCON21NM", "parl_const"], axis=1, inplace=True)
        fibre_by_constituency_geo = gpd.GeoDataFrame(
            fibre_by_constituency_geo, geometry=fibre_by_constituency_geo.geometry
        )
        choropleth_data, cmap = self.get_choropleth_for_uk_broadband_with_slider(
            fibre_by_constituency_geo, "FTTP", colormap=linear.Purples_07
        )
        return choropleth_data, cmap

    def get_europe_broadband_data(self):
        eu_broadband = pd.read_excel(
            "files/data/Broadband_Coverage_in_Europe_2023_Final_dataset_20240905_fymrNtGW8v3HudBU9eUqxiEp30_106734.xlsx",
            sheet_name="Data",
            skiprows=6,
        )
        eu_columns = [
            "Country",
            "Metric",
            "Geography level",
            2018,
            2019,
            2020,
            2021,
            2022,
            2023,
        ]
        eu_broadband = eu_broadband[eu_columns]
        eu_broadband_total = eu_broadband.query('`Geography level` == "Total"').query(
            '`Country` != "EU27" & `Country` != "EU28"'
        )
        eu_broadband_total.drop(columns=["Geography level"], inplace=True)
        eu_broadband_FTTP_per_household = eu_broadband_total.query(
            '`Metric` == "FTTP" | `Metric` == "Households"'
        )
        eu_broadband_fttp_melted = eu_broadband_FTTP_per_household.melt(
            id_vars=["Country", "Metric"],
            var_name="Year",
            value_name="Number of households",
        )
        eu_broadband_fttp_pivot = eu_broadband_fttp_melted.pivot(
            index=["Country", "Year"], columns="Metric", values="Number of households"
        )
        eu_broadband_fttp_pivot.reset_index(inplace=True)
        eu_broadband_fttp_pivot.rename_axis(columns=None, inplace=True)
        eu_broadband_fttp_pivot["Percentage of households with FTTP availability"] = (
            eu_broadband_fttp_pivot["FTTP"]
            / eu_broadband_fttp_pivot["Households"]
            * 100
        )
        return eu_broadband_fttp_pivot

    def get_constituencies(self) -> gpd.geodataframe.GeoDataFrame:
        constituencies = gpd.read_file(
            "files/data/Westminster_Parliamentary_Constituencies_Dec_2021_UK_BUC_2022_-8882165546947265805.zip"
        )
        constituencies["PCON21NM"] = constituencies["PCON21NM"].str.upper().str.strip()
        return constituencies[["PCON21CD", "PCON21NM", "geometry"]]

    def get_ofcom_full_fibre(self, file: str) -> pd.core.frame.DataFrame:
        ofcom_df = pd.read_csv(file, encoding="latin")
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
            2023: filename.substitute(year=2024, n="01", r="01"),
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
        years = [2018, 2019, 2020, 2021, 2022, 2023]
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
            data=gdf, styledict=styledict, date_options="YYYY"
        )
        return choropleth_with_slider, cmap

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

    def make_map_title(self, title: str, **kwargs) -> folium.Element:
        position = (
            "bottom: 0px; right: 0px"
            if "position" not in kwargs
            else kwargs["position"]
        )
        border = (
            "border:2px solid grey"
            if "border" not in kwargs
            else f'border:{kwargs["border"]}'
        )
        background = (
            "background-color:white"
            if "background-color" not in kwargs
            else f'background-color:{kwargs["background-color"]}'
        )
        font_size = (
            "font-size:16px"
            if "font-size" not in kwargs
            else 'font-size:kwargs["font-size"]'
        )
        title_html = f"""<h3 align="center" 
        style="position: fixed; {position};width:200px {border}; z-index:9999; {background};opacity: .85;{font_size};font-weight: bold;">
            <b>{title}</b>
        </h3>"""
        return folium.Element(title_html)

    def make_RUC_geojson_map(self, map: folium.Map):
        lgd_txt = '<span style="color: {col};">{txt}</span>'
        area_dict = {
            "Rural": "#ff0000",
            "Urban": "#0000cd",
            "Urban with rural areas": "#008000",
            "Sparse and rural": "#ffff00",
        }
        for area, color in area_dict.items():
            subset = self.constituencies_with_RUC[
                self.constituencies_with_RUC["Urban/Rural Classification"] == area
            ]
            fg = folium.FeatureGroup(name=lgd_txt.format(txt=area, col=color))
            folium.GeoJson(
                subset.geometry,
                style_function=lambda feature, color=color: {
                    "fillColor": color,
                    "color": "black",
                    "weight": 2,
                    "dashArray": "5, 5",
                },
            ).add_to(fg)
            fg.add_to(map)

        folium.LayerControl(collapsed=True).add_to(map)
        map.render()
        root = map.get_root()
        root.html.add_child(
            self.make_map_title(
                "Urban/Rural Classification<br>of<br>Parliamentary Constituencies"
            )
        )
        root.html.add_child(self.make_map_legend(area_dict))
        return map

    def make_map_legend(self, color_dict, **kwargs):
        position = (
            "bottom: 0px; right: 310px;"
            if "position" not in kwargs
            else kwargs["position"]
        )
        border = (
            "border:2px solid grey"
            if "border" not in kwargs
            else f'border:{kwargs["border"]}'
        )
        background = (
            "background-color:white"
            if "background-color" not in kwargs
            else f'background-color:{kwargs["background-color"]}'
        )
        font_size = (
            "font-size:14px"
            if "font-size" not in kwargs
            else 'font-size:kwargs["font-size"]'
        )
        legend_html = f"""
         <div style="
         position: fixed; 
         {position};width: 190px; height: 110px; 
         {border};z-index:9999; 
         {background};
         opacity: .85;
         {font_size};
         font-weight: bold;">&nbsp; <u>Legend</u>"""
        for area, color in color_dict.items():
            legend_html += f"""<br> &nbsp; {area} &nbsp; <i class="fa-solid fa-square" style="color:{color}"></i>"""
        return folium.Element(legend_html + "</div>")

    def add_script_to_map(self, map, script):
        script = folium.Element(script)
        return map.get_root().script.add_child(script)

    def make_RUC_dualmap(self):
        m = folium.plugins.DualMap(location=[54.7023545, -3.2765753], zoom_start=6)
        folium.TileLayer("cartodbpositron").add_to(m.m1)
        self.make_RUC_geojson_map(m.m2)
        choropleth = self.make_choropleth(
            self.constituencies_with_RUC,
            "Percentage of Premises with Full Fibre Availability",
            "",
            2024,
            False,
        )
        choropleth.add_to(m.m1)
        m.m1.render()
        root = m.m1.get_root()
        root.html.add_child(
            self.make_map_title(
                "Percentage of Premises<br>with Full Fibre Availability<br>by Constituency",
                **{"position": "left:1px;bottom:0px"},
            )
        )
        scripts = [
            "els=document.getElementsByClassName('folium-map');for(var i=0;i<els.length;i++){els[i].style.border='2px solid black'};",
            "els=document.getElementsByClassName('leaflet-control');els[0].style.display='None';",
        ]
        for script in scripts:
            self.add_script_to_map(m.m1, script)

        m.get_root().width = "1000px"
        m.get_root().height = "800px"
        return m.get_root()._repr_html_()

    def make_map_of_fibre_distribution_uk(self):
        m = folium.Map(
            location=[54.7023545, -3.2765753], zoom_start=6, height=750, width=500
        )
        choropleth_with_slider, colorbar = (
            self.get_choropleth_for_full_fibre_availability_with_slider(
                self.choropleth_data
            )
        )
        choropleth_with_slider.add_to(m)
        colorbar.caption = "Distribution of Fibre as a percentage"
        colorbar.add_to(m)
        m.get_root().width = "500px"
        m.get_root().height = "800px"
        m.get_root().html.add_child(
            self.make_map_title(
                "Distribution of Fibre<br>in the UK<br>between 2018-2024<br>by constituency'",
                **{"position": "left:1px;bottom:0px"},
            )
        )
        script = """els=document.getElementsByClassName('folium-map');for(var i=0;i<els.length;i++){
            els[i].style.border='2px solid black';els[i].style.overflow='hidden'};"""
        self.add_script_to_map(m, script)
        return m.get_root()._repr_html_()

    def make_eu_fftp_availability_map(self):
        m = folium.Map(
            location=[55.670249, 10.3333283], zoom_start=4, height=800, width=500
        )
        choropleth_with_slider, colorbar1 = self.eu_choropleth
        choropleth_with_slider.add_to(m)
        colorbar1.caption = "Percentage of households with FTTP availability"
        colorbar1.add_to(m)
        m.get_root().width = "500px"
        m.get_root().height = "800px"
        m.render()
        m.get_root().html.add_child(
            self.make_map_title(
                "Comparison between<br>FTTP availability<br>in the EU<br>and the UK",
                **{"position": "left:1px;bottom:0px"},
            )
        )
        script = """els=document.getElementsByClassName('folium-map');for(var i=0;i<els.length;i++){
            els[i].style.border='2px solid black';els[i].style.overflow='hidden'};"""
        self.add_script_to_map(m, script)
        return m.get_root()._repr_html_()

    def make_eu_fftp_availability_predictions_map(self):
        m = folium.Map(
            location=[55.670249, 10.3333283], zoom_start=4, height=800, width=500
        )
        choropleth_with_slider, colorbar1 = self.eu_choropleth_predictions
        choropleth_with_slider.add_to(m)
        colorbar1.caption = (
            "Prediction Of Percentage of households with FTTP availability"
        )
        colorbar1.add_to(m)
        m.get_root().width = "500px"
        m.get_root().height = "800px"
        m.render()
        m.get_root().html.add_child(
            self.make_map_title(
                "Prediction for<br>FTTP availability<br>in the EU<br>and the UK",
                **{"position": "left:1px;bottom:0px"},
            )
        )
        script = """els=document.getElementsByClassName('folium-map');for(var i=0;i<els.length;i++){
            els[i].style.border='2px solid black';els[i].style.overflow='hidden'};"""
        self.add_script_to_map(m, script)
        return m.get_root()._repr_html_()

    def make_map_of_fibre_predictions_uk(self):
        choropleth_with_slider, colorbar = self.prepare_constituency_predictions()

        m = folium.Map(
            location=[54.7023545, -3.2765753], zoom_start=6, height=750, width=500
        )
        choropleth_with_slider.add_to(m)
        colorbar.caption = "Distribution of Fibre as a percentage"
        colorbar.add_to(m)
        m.get_root().width = "500px"
        m.get_root().height = "800px"
        m.render()

        m.save("test.html")
        m.get_root().width = "500px"
        m.get_root().height = "800px"
        m.get_root().html.add_child(
            self.make_map_title(
                "Prediction of Fibre<br>in the UK<br>up to 2030<br>by constituency'",
                **{"position": "left:1px;bottom:0px"},
            )
        )
        script = """els=document.getElementsByClassName('folium-map');for(var i=0;i<els.length;i++){
            els[i].style.border='2px solid black';els[i].style.overflow='hidden'};"""
        self.add_script_to_map(m, script)
        return m.get_root()._repr_html_()
