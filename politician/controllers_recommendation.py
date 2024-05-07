from .models import RecommendedPoliticianLinkByPolitician

from politician.models import Politician
import pandas as pd
from sklearn.cluster import KMeans
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk
import warnings
import polars as pl

warnings.simplefilter("ignore")
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
nltk.download('punkt')


def add_cluster(df: pd.DataFrame, k: int = 300) -> pd.DataFrame:
    """
        Add a clustering column to the DataFrame using KMeans.
        Parameters:
        - df (pd.DataFrame): Input DataFrame.
        - k (int): Number of clusters for KMeans (default is 300).
        Returns:
        - pd.DataFrame: DataFrame with an additional 'Cluster' column.
        """

    try:
        kmeans = KMeans(n_clusters=k)
        kmeans.fit(df)
        df['Cluster'] = kmeans.labels_
        return df

    except Exception as e:
        df['Cluster'] = k
        return df


def make_flag(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
       Create flag columns show whether politician has social media or not in the DataFrame.
       Parameters:
       - df (pd.DataFrame): Input DataFrame.
       - col (str): Name of the column.
       Returns:
       - pd.DataFrame: DataFrame with an additional '{col}_flag' column.
    """

    if col in df.columns:
        target = df[[col]]
    else:
        return df
    # replace value with 1 and None with 0
    target = target.applymap(replacer)
    df[f'{col}_flag'] = target
    df = df.drop(col, axis=1)
    return df


def tfidf(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
        Calculate TF-IDF values for the twitter description column in the DataFrame.
        Parameters:
        - df (pd.DataFrame): Input DataFrame.
        - col (str): Name of the text column.
        Returns:
        - pd.DataFrame: DataFrame with additional columns for TF-IDF values.
    """

    if col not in df.columns:
        return pd.DataFrame()

    ps = PorterStemmer()
    sentences = list(df[col].fillna(""))
    sentences = [stemming(i, ps) for i in sentences]
    try:
        vectorized = TfidfVectorizer(stop_words='english', max_features=100)
        tfidf_matrix = vectorized.fit_transform(sentences)
        return pd.DataFrame(tfidf_matrix.toarray(), columns=vectorized.get_feature_names_out())
    except Exception as e:
        return pd.DataFrame()


def replacer(value):
    if value is None:
        return 0
    else:
        return 1


def stemming(sentence, ps):
    if sentence is None:
        return ""

    words = word_tokenize(sentence)
    output = ""
    for w in words:
        output += " "
        output += ps.stem(w)
    return output


def one_hot_add(df, category):
    if category not in df.columns:
        return df

    try:
        return pd.get_dummies(df, columns=[category], prefix=[category])

    except Exception as e:
        df = df.drop([category], axis=1)
        return df


def remove_minority(df: pd.DataFrame, col: str, num: int) -> pd.DataFrame:
    """
        Combine small parties in a DataFrame column into an 'Others' if their count is below a specified threshold.
        Parameters:
        - df (pd.DataFrame): Input DataFrame.
        - col (str): Name of the column containing party information.
        - num (int): Threshold count. Parties with counts less than or equal to this threshold will be combined into
        'Others'.
        Returns:
        - pd.DataFrame: DataFrame with small parties combined into 'Others' in the specified column.
    """

    if col not in df.columns:
        return df

    for i, k in dict(df[col].value_counts()).items():
        if k <= num:
            df = df.replace(to_replace=i, value="Others")
    return df


def update_recommend():
    """
        Update recommended politicians based on clustering and selection criteria.
        Returns:
        - None
    """

    """df of all politician data"""
    all_data = Politician.objects.values()
    df = pd.DataFrame(all_data)
    df = df.replace(np.NaN, None)

    """df of location of state"""
    state_df = pd.read_csv("politician/static/stateLocation/state_code.csv")

    """lower case"""
    df.political_party = df.political_party.str.lower()
    df.state_code = df.state_code.str.lower()
    df = pd.merge(df, state_df, on='state_code', how='left')
    del state_df

    for col in ['facebook_url', 'politician_phone_number', 'google_civic_candidate_name',
                'we_vote_hosted_profile_image_url_large', 'politician_email_address']:
        df = make_flag(df, col)

    all_we_need = ['we_vote_id', 'political_party', 'politician_url', 'state_code', 'twitter_followers_count',
                   'twitter_description', 'lon', 'lat'] + [item for item in df.columns if item.endswith("flag")]

    all_we_need = [col for col in df.columns if col in all_we_need]

    df = df[all_we_need]
    df = remove_minority(df, "political_party", 15)

    if 'political_party' in df.columns:
        df['political_party'] = df['political_party'].fillna('Others')

    if 'twitter_description' in df.columns:
        df['twitter_description'] = df['twitter_description'].fillna("")

    if 'lon' in df.columns:
        df['lon'] = df['lon'].fillna(-76.6413)

    if 'lat' in df.columns:
        df['lat'] = df['lat'].fillna(39.0458)

    one_hot_list = ['political_party']

    for col in one_hot_list:
        df = one_hot_add(df, col)

    df = df.reset_index(drop=True)

    for col in ["twitter_description"]:
        df = pd.concat([df, tfidf(df, col)], axis=1)

    drop_list = []
    ids = df['we_vote_id']

    for col in df.columns:
        if df[col].dtype != 'O':
            df[col] = (df[col] - np.mean(df[col])) / np.std(df[col])
        elif df[col].dtype == 'O':
            drop_list.append(col)

    df = df.drop(drop_list, axis=1)

    k = 300
    df = add_cluster(df, k)

    if int(np.mean(df['Cluster'])) == k:
        return 0

    df = pd.concat([ids, df], axis=1)
    df = pl.from_pandas(df)
    df = df.select(['Cluster', 'we_vote_id'])

    """choose 4 from same group, 1 from outside group"""
    bulk_update_list = []

    for clus in range(0, k):
        diff_df = df.filter(pl.col("Cluster") != clus)
        same_df = df.filter((pl.col("Cluster") == clus))
        size = same_df.shape[0]
        for we_id in same_df["we_vote_id"]:

            cand_list = []
            k = 5

            if size == 0:
                cand_list = diff_df.sample(k).select("we_vote_id").to_series().to_list()

            elif size < 4:
                temp_list = same_df.sample(size).select("we_vote_id").to_series().to_list()
                cand_list.extend(temp_list)
                k = k - len(cand_list)
                cand_list.extend(diff_df.sample(k).select("we_vote_id").to_series().to_list())

            else:
                temp_list = same_df.sample(k - 1).select("we_vote_id").to_series().to_list()
                cand_list.extend(temp_list)
                k = k - len(cand_list)
                cand_list.extend(diff_df.sample(k).select("we_vote_id").to_series().to_list())

            # no_duplicates
            cand_list = list(set(cand_list))

            if len(cand_list) == 5:
                for i in cand_list:
                    record = RecommendedPoliticianLinkByPolitician(
                        from_politician_we_vote_id=we_id,
                        recommended_politician_we_vote_id=i)
                    bulk_update_list.append(record)

    RecommendedPoliticianLinkByPolitician.objects.bulk_create(bulk_update_list)
