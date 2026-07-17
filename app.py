import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Moulin d'Aita - Traçabilité", page_icon="🌾", layout="wide")

st.title("🌽 Système de Traçabilité - Moulin d'Aita")
st.markdown("---")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Fonction pour charger les données proprement
def charger_onglet(nom_onglet, colonnes_defaut):
    try:
        df = conn.read(worksheet=nom_onglet, ttl=0)
        df = df.dropna(how='all') # Nettoie les lignes vides
        if df.empty:
            return pd.DataFrame(columns=colonnes_defaut)
        return df
    except Exception:
        return pd.DataFrame(columns=colonnes_defaut)

# Chargement des données en temps réel
df_moulin = charger_onglet("1 moulin", ["Date", "Produit", "N° Lot", "Quantité (kg)"])
df_talos = charger_onglet("2_Production_Talos", ["Date Fab.", "N° Lot / DLC", "Lot Farine", "Lot Mix", "Quantité"])

# --- FONCTION : GÉNÉRATION DU LOT MOULIN ---
def generer_numero_lot_moulin(date_obj, produit):
    if not date_obj or not produit:
        return ""
    premiere_lettre = produit[0].upper()
    annee_deux_chiffres = str(date_obj.year)[-2:]
    semaine = date_obj.isocalendar()[1]
    return f"{premiere_lettre}{annee_deux_chiffres}{semaine:02d}"

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
        
        soumettre = st.form_submit_button("Enregistrer la mouture dans Google Sheets")
        
        if soumettre:
            nouvelle_ligne = pd.DataFrame([{
                "Date": date_moulin.strftime("%Y-%m-%d"),
                "Produit": produit,
                "N° Lot": str(lot_calcule),
                "Quantité (kg)": quantite
            }])
            df_moulin = pd.concat([df_moulin, nouvelle_ligne], ignore_index=True)
            conn.update(worksheet="1 moulin", data=df_moulin)
            st.success(f"Lot {lot_calcule} enregistré avec succès !")
            st.rerun()

    st.markdown("---")
    st.subheader("Historique des Moutures")
    st.dataframe(df_moulin, use_container_width=True)

    if not df_moulin.empty:
        with st.expander("⚠️ Supprimer un lot de mouture par erreur"):
            liste_lots_moulin = df_moulin["N° Lot"].dropna().unique().tolist()
            lot_a_supprimer = st.selectbox("Sélectionner le lot à effacer :", ["-- Choisir --"] + liste_lots_moulin)
            
            if st.button("🗑️ Supprimer ce lot du Moulin", type="primary"):
                if lot_a_supprimer != "-- Choisir --":
                    df_moulin = df_moulin[df_moulin["N° Lot"] != lot_a_supprimer]
                    conn.update(worksheet="1 moulin", data=df_moulin)
                    st.success(f"Le lot {lot_a_supprimer} a été supprimé.")
                    st.rerun()

# -----------------------------------------------------------------
# PAGE 2 : PRODUCTION TALOS
# -----------------------------------------------------------------
elif navigation == "🥞 2. Production Talos":
    st.header("Enregistrement de la Production de Talos")
    
    lots_farine = df_moulin[df_moulin['Produit'] == 'Farine']['N° Lot'].dropna().unique().tolist()
    lots_mix = df_moulin[df_moulin['Produit'] == 'Mix']['N° Lot'].dropna().unique().tolist()
    
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
        st.warning(f"📅 **N° de Lot créé automatiquement (DLC) :** {lot_talos_genere}")
        
        soumettre_talos = st.form_submit_button("Enregistrer la fournée dans Google Sheets")
        
        if soumettre_talos:
            if not lot_f_choisi:
                st.error("Tu dois obligatoirement sélectionner un lot de farine.")
            else:
                nouvelle_fournee = pd.DataFrame([{
                    "Date Fab.": date_talos.strftime("%Y-%m-%d"),
                    "N° Lot / DLC": str(lot_talos_genere),
                    "Lot Farine": str(lot_f_choisi),
                    "Lot Mix": str(lot_m_choisi),
                    "Quantité": int(quantite_talos)
                }])
                df_talos = pd.concat([df_talos, nouvelle_fournee], ignore_index=True)
                conn.update(worksheet="2_Production_Talos", data=df_talos)
                st.success(f"Fournée enregistrée !")
                st.rerun()

    st.markdown("---")
    st.subheader("Historique de Fabrication des Talos")
    st.dataframe(df_talos, use_container_width=True)

    if not df_talos.empty:
        with st.expander("⚠️ Supprimer une fournée de Talos par erreur"):
            options_suppr = {f"Ligne {i} : Fait le {row['Date Fab.']} (DLC: {row['N° Lot / DLC']})": i for i, row in df_talos.iterrows()}
            choix_fournee = st.selectbox("Sélectionner la fournée à effacer :", ["-- Choisir --"] + list(options_suppr.keys()))
            
            if st.button("🗑️ Supprimer cette fournée de Talos", type="primary"):
                if choix_fournee != "-- Choisir --":
                    index_a_supprimer = options_suppr[choix_fournee]
                    df_talos = df_talos.drop(index_a_supprimer)
                    conn.update(worksheet="2_Production_Talos", data=df_talos)
                    st.success("La fournée a bien été supprimée.")
                    st.rerun()

# -----------------------------------------------------------------
# PAGE 3 : MOTEUR DE RECHERCHE
# -----------------------------------------------------------------
elif navigation == "🔍 3. Moteur de Recherche":
    st.header("Moteur de Recherche & Généalogie des Lots")
    
    liste_lots_talos = df_talos['N° Lot / DLC'].dropna().unique().tolist()
    recherche = st.selectbox("Sélectionner le N° de lot (DLC) du Talo à tracer :", ["-- Choisir un lot --"] + liste_lots_talos)
    
    if recherche and recherche != "-- Choisir un lot --":
        st.markdown(f"### 🧬 Arbre Généalogique du Lot Talos : `{recherche}`")
        
        df_talos_trouve = df_talos[df_talos['N° Lot / DLC'] == recherche]
        
        if not df_talos_trouve.empty:
            row_t = df_talos_trouve.iloc[0]
            
            st.success(f"""
            **🥞 Étape 1 : Produit Fini (Talos)**
            *   **Date de Fabrication :** {row_t['Date Fab.']}
            *   **Date Limite de Consommation (Lot) :** {row_t['N° Lot / DLC']}
            *   **Quantité fabriquée :** {row_t['Quantité']} pièces
            """)
            
            lot_f = row_t['Lot Farine']
            lot_m = row_t['Lot Mix'] # --- CORRECTION ICI (Nom de variable uniformisé) ---
            
            st.write("#### ⬇️ Remontée vers les Matières Premières (Moulin) :")
            col_f, col_m = st.columns(2)
            
            with col_f:
                if lot_f and str(lot_f) != "nan" and lot_f != "":
                    df_f_moulin = df_moulin[df_moulin['N° Lot'] == lot_f]
                    if not df_f_moulin.empty:
                        st.info(f"""
                        **🌾 Origine de la Farine**
                        *   **N° Lot utilisé :** `{lot_f}`
                        *   **Date de mouture :** {df_f_moulin.iloc[0]['Date']}
                        *   **Quantité moulue ce jour-là :** {df_f_moulin.iloc[0]['Quantité (kg)']} kg
                        """)
                    else:
                        st.error(f"❌ Le lot de farine `{lot_f}` est introuvable au moulin.")
            
            with col_m:
                if lot_m and str(lot_m) != "nan" and lot_m != "":
                    df_m_moulin = df_moulin[df_moulin['N° Lot'] == lot_m]
                    if not df_m_moulin.empty:
                        st.info(f"""
                        **🥣 Origine du Mix**
                        *   **N° Lot utilisé :** `{lot_m}`
                        *   **Date de mouture :** {df_m_moulin.iloc[0]['Date']}
                        *   **Quantité moulue ce jour-là :** {df_m_moulin.iloc[0]['Quantité (kg)']} kg
                        """)
                    else:
                        st.error(f"❌ Le lot de mix `{lot_m}` est introuvable au moulin.")
                else:
                    st.write("*Aucun lot de Mix n'a été nécessaire pour cette fournée.*")
