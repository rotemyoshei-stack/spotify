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

# קיצור לשימוש נוח
h = fix_hebrew

# --- בחירת תיקייה ---
st.sidebar.header(h("📂 בחירת תיקייה"))
folder_name = st.sidebar.text_input(h("שם תיקייה עם קבצי JSON"), "data_folder")

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
        st.sidebar.success(h(f"✅ נטענו {len(json_files)} קבצים"))
    else:
        st.sidebar.warning(h("⚠️ אין קבצי JSON בתיקייה"))
        df = None
else:
    st.sidebar.warning(h("⚠️ התיקייה לא קיימת"))
    df = None

if df is not None and not df.empty:
    # --- עיבוד ראשוני ---
    # שומרים עותק מקורי לשימוש פנימי, ונכין עותק להצגה
    # (לא משנים שמות העמודות המקוריות כי הקוד משתמש בהן)
    df['endTime'] = pd.to_datetime(df['endTime'])
    df['secondsPlayed'] = df['msPlayed'] / 1000
    df['timePlayed'] = pd.to_timedelta(df['secondsPlayed'], unit='second')
    df['startTime'] = df['endTime'] - df['timePlayed']
    df['weekNum'] = df['startTime'].dt.isocalendar().week

    st.header(h("🎧 ברוכים הבאים — Spotify Wrapped משודרג"))

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

    st.header(h("📊 אחוזי האזנה לשירים"))

    if not aggregated_data.empty:
        # הצגה ידידותית בעברית של הטבלה
        aggregated_display = aggregated_data.copy()
        aggregated_display['trackName'] = aggregated_display['trackName'].apply(lambda x: h(x) if isinstance(x, str) else x)
        aggregated_display['artistName'] = aggregated_display['artistName'].apply(lambda x: h(x) if isinstance(x, str) else x)
        aggregated_display.rename(columns={
            'trackName': h('שם שיר'),
            'artistName': h('שם אמן'),
            'avg_play_time': h('משך ממוצע'),
            'times_played': h('כמות האזנות'),
            'max_song_length': h('אורך שיר מקסימלי'),
            'avg_percentage': h('אחוז האזנה')
        }, inplace=True)

        st.dataframe(aggregated_display.head(15))

        # בחירת השיר הטוב והגרוע (בהתאם לסינון הנ"ל)
        best_song = aggregated_data.sort_values(by=['times_played','avg_percentage'], ascending=[False, False]).iloc[0]
        worst_song = aggregated_data.sort_values(by='avg_percentage', ascending=True).iloc[0]

        st.success(h("🎶 השיר עם אחוז ההאזנה הגבוה ביותר הוא ") + " " + h(best_song['trackName']) + f" ({best_song['avg_percentage']:.1f}%)")
        st.warning(h("⚠️ השיר עם אחוז ההאזנה הנמוך ביותר הוא ") + " " + h(worst_song['trackName']) + f" ({worst_song['avg_percentage']:.1f}%)")

        # גרף ברים לשירים עם אחוזים נמוכים
        st.subheader(h("📉 שירים עם אחוזי האזנה נמוכים ביותר"))
        low_songs = aggregated_data.sort_values(by='avg_percentage').head(5)
        if not low_songs.empty:
            fig, ax = plt.subplots(figsize=(8,4))
            x = low_songs['trackName'].apply(lambda s: h(s) if isinstance(s, str) else s)
            y = low_songs['avg_percentage']
            ax.bar(x, y)
            ax.set_xlabel(h('שם שיר'))
            ax.set_ylabel(h('אחוז האזנה'))
            ax.set_title(h('שירים עם אחוזי_
