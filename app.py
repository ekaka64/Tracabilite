import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Moulin d'Aita - Traçabilité", page_icon="🌾", layout="wide")

# --- CONNEXION BASE DE DONNÉES (SQLite) ---
conn = sqlite3.connect("tracabilite_moulin.db", check_same_thread=False)
cursor = conn.cursor()

# Création des tables si elles n'existent pas
cursor.execute("""
CREATE TABLE IF NOT EXISTS moulin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    produit TEXT,
    lot TEXT,
    quantite REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS production_talos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    lot_talos TEXT,
    lot_farine TEXT,
    lot_mix TEXT,
    quantite_talos INTEGER
)
""")
conn.commit()

# Sécurité : Ajout de la colonne lot_talos si le fichier existait déjà avant
try:
    cursor.execute("ALTER TABLE production_talos ADD COLUMN lot_talos TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass

# --- FONCTION : GÉNÉRATION DU LOT MOULIN ---
def generer_numero_lot_moulin(date_obj, produit):
    if not date_obj or not produit:
        return ""
    premiere_lettre = produit[0].upper()
    annee_deux_chiffres = str(date_obj.year)[-2:]
    semaine = date_obj.isocalendar()[1]
    return f"{premiere_lettre}{annee_deux_chiffres}{semaine:02d}"

# --- INTERFACE STREAMLIT ---
st.title("🌽 Système de Traçabilité - Moulin d'Aita")
st.markdown("---")

# Navigation latérale
navigation = st.sidebar.radio("Navigation", ["🌾 1. Moulin (Moutures)", "🥞 2. Production Talos", "🔍 3. Moteur de Recherche"])

# -----------------------------------------------------------------
# PAGE 1 : MOULIN
# -----------------------------------------------------------------
if navigation == "🌾 1. Moulin (Moutures)":
    st.header("Enregistrement des Moutures au Moulin")
    
    with st.form("form_moulin", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            date_moulin = st.date_input("Date de la mouture", datetime.now())
        with col2:
            produit = st.selectbox("Produit créé", ["Farine", "Mix", "Polenta", "Bihia"])
        with col3:
            quantite = st.number_input("Quantité produite (en kg)", min_value=0.0, step=0.5)
            
        lot_calcule = generer_numero_lot_moulin(date_moulin, produit)
        st.info(f"**Numéro de lot qui sera généré automatiquement :** {lot_calcule}")
        
        soumettre = st.form_submit_button("Enregistrer la mouture")
        
        if soumettre:
            cursor.execute(
                "INSERT INTO moulin (date, produit, lot, quantite) VALUES (?, ?, ?, ?)",
                (date_moulin.strftime("%Y-%m-%d"), produit, lot_calcule, quantite)
            )
            conn.commit()
            st.success(f"Lot {lot_calcule} enregistré avec succès !")
            st.rerun()

    st.markdown("---")
    st.subheader("Historique des Moutures")
    df_moulin = pd.read_sql_query("SELECT date as Date, produit as Produit, lot as [N° Lot], quantite as [Quantité (kg)] FROM moulin ORDER BY id DESC", conn)
    st.dataframe(df_moulin, use_container_width=True)

    # --- AJOUT : BOUTON SUPPRIMER LOT MOULIN ---
    if not df_moulin.empty:
        with st.expander("⚠️ Supprimer un lot de mouture par erreur"):
            liste_lots_moulin = df_moulin["N° Lot"].unique().tolist()
            lot_a_supprimer = st.selectbox("Sélectionner le lot à effacer définitivement :", ["-- Choisir --"] + liste_lots_moulin, key="del_moulin_select")
            
            if st.button("🗑️ Supprimer ce lot du Moulin", type="primary", key="btn_del_moulin"):
                if lot_a_supprimer != "-- Choisir --":
                    cursor.execute("DELETE FROM moulin WHERE lot = ?", (lot_a_supprimer,))
                    conn.commit()
                    st.success(f"Le lot {lot_a_supprimer} a bien été supprimé de la base de données.")
                    st.rerun()
                else:
                    st.warning("Veuillez sélectionner un lot valide.")

# -----------------------------------------------------------------
# PAGE 2 : PRODUCTION TALOS
# -----------------------------------------------------------------
elif navigation == "🥞 2. Production Talos":
    st.header("Enregistrement de la Production de Talos")
    
    df_lots = pd.read_sql_query("SELECT lot, produit FROM moulin", conn)
    lots_farine = df_lots[df_lots['produit'] == 'Farine']['lot'].tolist()
    lots_mix = df_lots[df_lots['produit'] == 'Mix']['lot'].tolist()
    
    with st.form("form_talos", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_talos = st.date_input("Date de fabrication", datetime.now())
            quantite_talos = st.number_input("Nombre de Talos fabriqués", min_value=0, step=1)
        with col2:
            lot_f_choisi = st.selectbox("Sélectionner le Lot de Farine utilisé", [""] + lots_farine)
            lot_m_choisi = st.selectbox("Sélectionner le Lot de Mix utilisé (Optionnel)", [""] + lots_mix)
            
        date_dlc = date_talos + timedelta(weeks=3)
        lot_talos_genere = date_dlc.strftime("%d/%m/%Y")
        
        st.warning(f"📅 **N° de Lot créé automatiquement (DLC à +3 semaines) :** {lot_talos_genere}")
        
        soumettre_talos = st.form_submit_button("Enregistrer la fournée")
        
        if soumettre_talos:
            if not lot_f_choisi:
                st.error("Tu dois obligatoirement sélectionner un lot de farine.")
            else:
                cursor.execute(
                    "INSERT INTO production_talos (date, lot_talos, lot_farine, lot_mix, quantite_talos) VALUES (?, ?, ?, ?, ?)",
                    (date_talos.strftime("%Y-%m-%d"), lot_talos_genere, lot_f_choisi, lot_m_choisi, quantite_talos)
                )
                conn.commit()
                st.success(f"Fournée de Talos enregistrée ! Lot/DLC : {lot_talos_genere}")
                st.rerun()

    st.markdown("---")
    st.subheader("Historique de Fabrication des Talos")
    df_talos = pd.read_sql_query("SELECT id, date as [Date Fab.], lot_talos as [N° Lot / DLC], lot_farine as [Lot Farine], lot_mix as [Lot Mix], quantite_talos as [Quantité] FROM production_talos ORDER BY id DESC", conn)
    # On affiche le tableau sans la colonne ID technique pour l'utilisateur
    st.dataframe(df_talos.drop(columns=["id"]), use_container_width=True)

    # --- AJOUT : BOUTON SUPPRIMER FOURNÉE TALOS ---
    if not df_talos.empty:
        with st.expander("⚠️ Supprimer une fournée de Talos par erreur"):
            # On crée un affichage lisible "ID - Date - DLC" pour être sûr de supprimer la bonne ligne s'il y a des doublons de DLC
            options_suppr = {f"Option {row['id']} : Fait le {row['Date Fab.']} (DLC: {row['N° Lot / DLC']})": row['id'] for _, row in df_talos.iterrows()}
            choix_fournee = st.selectbox("Sélectionner la fournée à effacer définitivement :", ["-- Choisir --"] + list(options_suppr.keys()), key="del_talos_select")
            
            if st.button("🗑️ Supprimer cette fournée de Talos", type="primary", key="btn_del_talos"):
                if choix_fournee != "-- Choisir --":
                    id_a_supprimer = options_suppr[choix_fournee]
                    cursor.execute("DELETE FROM production_talos WHERE id = ?", (id_a_supprimer,))
                    conn.commit()
                    st.success("La fournée a bien été supprimée de la base de données.")
                    st.rerun()
                else:
                    st.warning("Veuillez sélectionner une fournée valide.")

# -----------------------------------------------------------------
# PAGE 3 : MOTEUR DE RECHERCHE
# -----------------------------------------------------------------
elif navigation == "🔍 3. Moteur de Recherche":
    st.header("Moteur de Recherche & Généalogie des Lots")
    
    df_t_lots = pd.read_sql_query("SELECT DISTINCT lot_talos FROM production_talos WHERE lot_talos IS NOT NULL AND lot_talos != ''", conn)
    liste_lots_talos = df_t_lots['lot_talos'].tolist()
    
    recherche = st.selectbox("Sélectionner le N° de lot (DLC) du Talo à tracer :", ["-- Choisir un lot --"] + liste_lots_talos)
    
    if recherche and recherche != "-- Choisir un lot --":
        st.markdown(f"### 🧬 Arbre Généalogique du Lot Talos : `{recherche}`")
        
        df_talos_trouve = pd.read_sql_query("SELECT * FROM production_talos WHERE lot_talos = ?", conn, params=(recherche,))
        
        if not df_talos_trouve.empty:
            row_t = df_talos_trouve.iloc[0]
            
            st.success(f"""
            **🥞 Étape 1 : Produit Fini (Talos)**
            *   **Date de Fabrication :** {row_t['date']}
            *   **Date Limite de Consommation (Lot) :** {row_t['lot_talos']}
            *   **Quantité fabriquée :** {row_t['quantite_talos']} pièces
            """)
            
            lot_f = row_t['lot_farine']
            lot_m = row_t['lot_mix']
            
            st.write("#### ⬇️ Remontée vers les Matières Premières (Moulin) :")
            col_f, col_m = st.columns(2)
            
            with col_f:
                if lot_f:
                    df_f_moulin = pd.read_sql_query("SELECT * FROM moulin WHERE lot = ?", conn, params=(lot_f,))
                    if not df_f_moulin.empty:
                        st.info(f"""
                        **🌾 Origine de la Farine**
                        *   **N° Lot utilisé :** `{lot_f}`
                        *   **Date de mouture :** {df_f_moulin.iloc[0]['date']}
                        *   **Quantité moulue ce jour-là :** {df_f_moulin.iloc[0]['quantite']} kg
                        """)
                    else:
                        st.error(f"❌ Le lot de farine `{lot_f}` est introuvable au moulin.")
            
            with col_m:
                if lot_m:
                    df_m_moulin = pd.read_sql_query("SELECT * FROM moulin WHERE lot = ?", conn, params=(lot_m,))
                    if not df_m_moulin.empty:
                        st.info(f"""
                        **🥣 Origine du Mix**
                        *   **N° Lot utilisé :** `{lot_m}`
                        *   **Date de mouture :** {df_m_moulin.iloc[0]['date']}
                        *   **Quantité moulue ce jour-là :** {df_m_moulin.iloc[0]['quantite']} kg
                        """)
                    else:
                        st.error(f"❌ Le lot de mix `{lot_m}` est introuvable au moulin.")
                else:
                    st.write("*Aucun lot de Mix n'a été nécessaire pour cette fournée.*")