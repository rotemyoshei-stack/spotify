import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import arabic_reshaper
from bidi.algorithm import get_display
import os, json

# --- פונקציה לסידור טקסט בעברית ---
def fix_hebrew(text):
    if isinstance(text, str):
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    return text
    
# --- בחירת תיקייה ---
st.sidebar.header("📂 בחירת תיקייה")
folder_name = st.sidebar.text_input(fix_hebrew("שם תיקייה עם קבצי JSON"), "data_folder")

# נבדוק אם התיקייה קיימת
if os.path.exists(folder_name) and os.path.isdir(folder_name):
    json_files = [f for f in os.listdir(folder_name) if f.endswith(".json")]
    
    if json_files:
        all_data = []
        for file_name in json_files:
            file_path = os.path.join(folder_name, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data if isinstance(data, list) else [data])
        
        df = pd.DataFrame(all_data)
        st.sidebar.success(fix_hebrew(f"✅ נטענו {len(json_files)} קבצים"))
    else:
        st.sidebar.warning(fix_hebrew("⚠️ אין קבצי JSON בתיקייה"))
        df = None
else:
    st.sidebar.warning(fix_hebrew("⚠️ התיקייה לא קיימת"))
    df = None

if df is not None:
    # --- עיבוד ראשוני ---
    df['endTime'] = pd.to_datetime(df['endTime'])
    df['secondsPlayed'] = df['msPlayed']/1000
    df['timePlayed'] = pd.to_timedelta(df['secondsPlayed'], unit='second')
    df['startTime'] = df['endTime'] - df['timePlayed']
    df['weekNum'] = df['startTime'].dt.isocalendar().week

    st.header(fix_hebrew("🎧 ברוכים הבאים ל־Spotify Wrapped משודרג"))

    # --- ניתוח אחוזי האזנה ---
    aggregated_data = df.groupby(['trackName','artistName']).agg(
        avg_play_time=('timePlayed', 'mean'),
        times_played=('trackName', 'count'),
        max_song_length=('timePlayed', 'max')
    ).reset_index()

    aggregated_data['avg_percentage'] = (aggregated_data['avg_play_time'] / aggregated_data['max_song_length'])*100
    aggregated_data = aggregated_data[aggregated_data['times_played'] > 1]
    aggregated_data = aggregated_data[aggregated_data['max_song_length'] > pd.Timedelta(seconds=60)]
    aggregated_data = aggregated_data.sort_values(by='avg_percentage', ascending=False)

    st.header(fix_hebrew("📊 אחוזי האזנה לשירים"))

    best_song = aggregated_data.sort_values(by=['times_played','avg_percentage']).iloc[0]
    worst_song = aggregated_data.iloc[-1]
    st.success(fix_hebrew(f"🎶 השיר עם אחוז ההאזנה הגבוה ביותר הוא **{best_song['trackName']}** ({best_song['avg_percentage']:.1f}%)"))
    st.warning(fix_hebrew(f"⚠️ השיר עם אחוז ההאזנה הנמוך ביותר הוא **{worst_song['trackName']}** ({worst_song['avg_percentage']:.1f}%)"))

    # גרף ברים לנטישה
    st.subheader(fix_hebrew("📉 שירים עם אחוזי האזנה נמוכים ביותר"))
    low_songs = aggregated_data.sort_values(by='avg_percentage').head(5)
    df_melted = low_songs.melt(
        id_vars='trackName',
        value_vars=['times_played','avg_percentage'],
        var_name='_
