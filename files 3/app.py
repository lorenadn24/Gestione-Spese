import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json, os, hashlib
from datetime import datetime, date

# ──────────────────────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="💰 Budget Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

USERS_FILE            = "users.json"
DATA_FILE             = "transactions.json"
STARTING_BALANCE_FILE = "starting_balance.json"

C_IN  = "#0BAD75"
C_OUT = "#E53E5B"
C_ACC = "#6B4FD8"
C_BG  = "#F4F6FB"
C_S1  = "#FFFFFF"
C_S2  = "#EBF0F8"
C_TXT = "#1A202C"
C_MUT = "#718096"
C_SDB = "#EEF2FF"
C_BRD = "#D8DFF0"

CAT_ENTRATA = ["Cassa"]
CAT_USCITA  = ["Luce", "Acqua", "Metano", "Commissioni bollette", "Acquisti vari", "Altro"]

MESI = {1:"Gen",2:"Feb",3:"Mar",4:"Apr",5:"Mag",6:"Giu",
        7:"Lug",8:"Ago",9:"Set",10:"Ott",11:"Nov",12:"Dic"}
MESI_FULL = {1:"Gennaio",2:"Febbraio",3:"Marzo",4:"Aprile",5:"Maggio",6:"Giugno",
             7:"Luglio",8:"Agosto",9:"Settembre",10:"Ottobre",11:"Novembre",12:"Dicembre"}

# ──────────────────────────────────────────────────────────────
#  UTILITÀ
# ──────────────────────────────────────────────────────────────
def hex_rgba(h, a):
    h = h.lstrip("#")
    r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

# ──────────────────────────────────────────────────────────────
#  CSS  — tutto pre-calcolato, nessuna funzione dentro la stringa
# ──────────────────────────────────────────────────────────────
def inject_css():
    badge_admin_bg  = hex_rgba(C_OUT, 0.13)
    badge_viewer_bg = hex_rgba(C_IN,  0.13)
    tag_bg          = hex_rgba(C_ACC, 0.15)

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif !important;
    background-color: {C_BG} !important;
    color: {C_TXT} !important;
}}
section[data-testid="stSidebar"] {{
    background: {C_SDB} !important;
    border-right: 1px solid {C_BRD} !important;
}}
section[data-testid="stSidebar"] * {{ color: {C_TXT} !important; }}

.block-container {{ padding: 1.8rem 2.5rem 3rem !important; }}

.stButton > button {{
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: 1px solid {C_BRD} !important;
    color: {C_TXT} !important;
    background: {C_S1} !important;
    transition: all .15s !important;
}}
.stButton > button[kind="primary"] {{
    background: {C_ACC} !important;
    border: none !important;
    color: white !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: #7B5FE8 !important;
    transform: translateY(-1px) !important;
}}

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea textarea,
.stSelectbox > div > div,
.stDateInput > div > div > input {{
    background: {C_S2} !important;
    border: 1px solid {C_BRD} !important;
    color: {C_TXT} !important;
    border-radius: 8px !important;
}}

details {{
    background: {C_S1} !important;
    border: 1px solid {C_BRD} !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(100,120,180,.06) !important;
}}
summary {{ color: {C_TXT} !important; font-weight: 500 !important; }}

.badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: .5px;
}}
.badge-admin  {{ background: {badge_admin_bg};  color: {C_OUT}; }}
.badge-editor {{ background: rgba(192,120,0,.13); color: #C07800; }}
.badge-viewer {{ background: {badge_viewer_bg}; color: {C_IN}; }}

hr {{ border-color: {C_BRD} !important; }}
span[data-baseweb="tag"] {{ background: {tag_bg} !important; color: {C_ACC} !important; }}
::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-thumb {{ background: {C_BRD}; border-radius: 4px; }}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
#  FILE I/O
# ──────────────────────────────────────────────────────────────
def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def _rj(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _wj(p, o):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, indent=2, ensure_ascii=False)

DEFAULT_USERS = {
    "admin":    {"password": _hash("admin123"), "role": "admin",  "display_name": "Admin"},
    "mariella": {"password": _hash("mariella"), "role": "editor", "display_name": "Mariella"},
    "seby":     {"password": _hash("seby"),     "role": "viewer", "display_name": "Seby"},
}

def load_users():
    if not os.path.exists(USERS_FILE):
        _wj(USERS_FILE, DEFAULT_USERS)
        return dict(DEFAULT_USERS)
    u = _rj(USERS_FILE)
    changed = False
    for k, v in DEFAULT_USERS.items():
        if k not in u:
            u[k] = v
            changed = True
    if changed:
        _wj(USERS_FILE, u)
    return u

def save_users(u):
    _wj(USERS_FILE, u)

def load_tx():
    return _rj(DATA_FILE) if os.path.exists(DATA_FILE) else []

def save_tx(d):
    _wj(DATA_FILE, d)

def load_sb():
    if not os.path.exists(STARTING_BALANCE_FILE):
        return {"initial": 0.0}
    return _rj(STARTING_BALANCE_FILE)

def save_sb(d):
    _wj(STARTING_BALANCE_FILE, d)

def next_id(data):
    return max((t["id"] for t in data), default=0) + 1

# ──────────────────────────────────────────────────────────────
#  DATAFRAME & RIMANENZA
# ──────────────────────────────────────────────────────────────
def get_df():
    data = load_tx()
    if not data:
        return pd.DataFrame(columns=["id","data","tipo","categoria","descrizione","importo","note"])
    df = pd.DataFrame(data)
    df["data"]  = pd.to_datetime(df["data"])
    df["anno"]  = df["data"].dt.year
    df["mese"]  = df["data"].dt.month
    return df

def get_rimanenza(df_all, year):
    initial = float(load_sb().get("initial", 0.0))
    if df_all.empty:
        return initial
    prev = df_all[df_all["anno"] < year]
    if prev.empty:
        return initial
    signed = prev.apply(
        lambda r: r["importo"] if r["tipo"] == "Entrata" else -r["importo"], axis=1
    ).sum()
    return initial + signed

def available_years(df):
    cur = datetime.now().year
    years = sorted(df["anno"].unique().tolist(), reverse=True) if not df.empty else []
    if cur not in years:
        years.insert(0, cur)
    return years

# ──────────────────────────────────────────────────────────────
#  AUTH
# ──────────────────────────────────────────────────────────────
def login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown(f"<h1 style='text-align:center; color:{C_TXT};'>💰 Budget Tracker</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; color:{C_MUT};'>Gestisci entrate e uscite</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Entra", type="primary", use_container_width=True):
            users = load_users()
            if username in users and users[username]["password"] == _hash(password):
                st.session_state.update(
                    logged_in=True,
                    username=username,
                    role=users[username]["role"],
                    display_name=users[username].get("display_name", username)
                )
                st.rerun()
            else:
                st.error("Username o password errati.")

def require_auth():
    if not st.session_state.get("logged_in"):
        login_page()
        st.stop()

def can_edit():
    return st.session_state.get("role") in ("admin", "editor")

def is_admin():
    return st.session_state.get("role") == "admin"

# ──────────────────────────────────────────────────────────────
#  SIDEBAR
# ──────────────────────────────────────────────────────────────
def sidebar(df_all):
    with st.sidebar:
        role = st.session_state.role
        st.markdown(
            f"<div style='margin-bottom:.3rem;'>"
            f"<span style='font-weight:700; font-size:1rem;'>👤 {st.session_state.display_name}</span><br>"
            f"<span class='badge badge-{role}'>{role.upper()}</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        st.divider()

        pages = ["📊 Dashboard", "📋 Transazioni"]
        if can_edit():
            pages.append("➕ Nuova Voce")
        if is_admin():
            pages.append("👥 Utenti")
        page = st.radio("", pages, label_visibility="collapsed")
        st.divider()

        years = available_years(df_all)
        selected_year = st.selectbox("📅 Anno", years)

        # Riepilogo numerico nella sidebar
        if not df_all.empty:
            dy      = df_all[df_all["anno"] == selected_year]
            rim     = get_rimanenza(df_all, selected_year)
            tot_in  = dy[dy["tipo"] == "Entrata"]["importo"].sum()
            tot_out = dy[dy["tipo"] == "Uscita"]["importo"].sum()
            saldo   = rim + tot_in - tot_out
            cs      = C_IN if saldo >= 0 else C_OUT

            st.markdown(
                f"<div style='background:{C_S1}; border:1px solid {C_BRD}; border-radius:10px;"
                f"padding:.9rem 1rem; font-size:.82rem;'>"
                f"<div style='color:{C_MUT}; font-weight:700; font-size:.65rem; letter-spacing:.8px;"
                f"text-transform:uppercase; margin-bottom:.5rem;'>RIEPILOGO {selected_year}</div>"
                f"<div style='display:flex; justify-content:space-between; margin-bottom:.2rem;'>"
                f"<span style='color:{C_MUT}; font-size:.75rem;'>Rimanenza</span>"
                f"<span style='color:{C_ACC}; font-family:monospace; font-weight:700; font-size:.75rem;'>€{rim:,.2f}</span>"
                f"</div>"
                f"<div style='display:flex; justify-content:space-between; margin-bottom:.2rem;'>"
                f"<span>Entrate</span>"
                f"<span style='color:{C_IN}; font-family:monospace; font-weight:700;'>+€{tot_in:,.2f}</span>"
                f"</div>"
                f"<div style='display:flex; justify-content:space-between; margin-bottom:.2rem;'>"
                f"<span>Uscite</span>"
                f"<span style='color:{C_OUT}; font-family:monospace; font-weight:700;'>-€{tot_out:,.2f}</span>"
                f"</div>"
                f"<div style='border-top:1px solid {C_BRD}; margin:.4rem 0;'></div>"
                f"<div style='display:flex; justify-content:space-between; font-weight:700;'>"
                f"<span>Saldo</span>"
                f"<span style='color:{cs}; font-family:monospace;'>€{saldo:,.2f}</span>"
                f"</div></div>",
                unsafe_allow_html=True
            )

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    return page, selected_year

# ──────────────────────────────────────────────────────────────
#  GRAFICI
# ──────────────────────────────────────────────────────────────
BASE_LAYOUT = dict(
    plot_bgcolor  = "rgba(0,0,0,0)",
    paper_bgcolor = "rgba(0,0,0,0)",
    font          = dict(family="Inter, sans-serif", color=C_TXT),
    margin        = dict(l=0, r=0, t=10, b=0),
)

def chart_barre_mensili(df):
    """Entrate vs Uscite raggruppate per mese."""
    m = df.groupby(["mese","tipo"])["importo"].sum().reset_index()
    m["mese_label"] = m["mese"].map(MESI)
    fig = px.bar(
        m, x="mese_label", y="importo", color="tipo",
        barmode="group",
        color_discrete_map={"Entrata": C_IN, "Uscita": C_OUT},
        labels={"importo": "€", "mese_label": "", "tipo": ""},
        category_orders={"mese_label": list(MESI.values())}
    )
    fig.update_layout(
        **BASE_LAYOUT,
        height=300,
        legend=dict(orientation="h", y=1.1, x=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=C_BRD, tickprefix="€")
    )
    fig.update_traces(marker_line_width=0, opacity=0.9)
    return fig

def chart_donut_uscite(df):
    """Torta uscite per categoria."""
    sub = df[df["tipo"] == "Uscita"]
    if sub.empty:
        return None
    cat = sub.groupby("categoria")["importo"].sum().reset_index()
    fig = px.pie(
        cat, names="categoria", values="importo", hole=0.50,
        color_discrete_sequence=[
            C_OUT, "#F6A623", "#F7CE46", C_IN,
            C_ACC, "#48CAE4", "#FF8C42", "#C77DFF", "#06D6A0"
        ]
    )
    fig.update_layout(
        **BASE_LAYOUT,
        height=300,
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont_size=11,
        marker=dict(line=dict(color="#FFFFFF", width=2))
    )
    return fig

def chart_saldo_cumulativo(df, rimanenza=0.0):
    """Area del saldo nel tempo, partendo dalla rimanenza."""
    d = df.sort_values("data").copy()
    d["signed"] = d.apply(
        lambda r: r["importo"] if r["tipo"] == "Entrata" else -r["importo"], axis=1
    )
    d["cum"] = d["signed"].cumsum() + rimanenza

    fig = go.Figure()
    # Tratto positivo
    pos = d[d["cum"] >= 0]
    if not pos.empty:
        fig.add_trace(go.Scatter(
            x=pos["data"], y=pos["cum"],
            mode="lines",
            fill="tozeroy",
            line=dict(color=C_IN, width=2.5),
            fillcolor=hex_rgba(C_IN, 0.15),
            showlegend=False
        ))
    # Tratto negativo
    neg = d[d["cum"] < 0]
    if not neg.empty:
        fig.add_trace(go.Scatter(
            x=neg["data"], y=neg["cum"],
            mode="lines",
            fill="tozeroy",
            line=dict(color=C_OUT, width=2.5),
            fillcolor=hex_rgba(C_OUT, 0.15),
            showlegend=False
        ))

    fig.update_layout(
        **BASE_LAYOUT,
        height=270,
        xaxis=dict(showgrid=False, color=C_MUT),
        yaxis=dict(gridcolor=C_BRD, tickprefix="€", color=C_MUT)
    )
    return fig

def chart_uscite_per_categoria(df):
    """Barre orizzontali uscite per categoria, ordinate per importo."""
    sub = df[df["tipo"] == "Uscita"]
    if sub.empty:
        return None
    cat = sub.groupby("categoria")["importo"].sum().reset_index().sort_values("importo")
    fig = px.bar(
        cat, x="importo", y="categoria", orientation="h",
        labels={"importo": "€", "categoria": ""},
        color="importo",
        color_continuous_scale=["#FFCCD5", C_OUT, "#8B0000"]
    )
    fig.update_layout(
        **BASE_LAYOUT,
        height=270,
        coloraxis_showscale=False,
        xaxis=dict(tickprefix="€", color=C_MUT),
        yaxis=dict(color=C_TXT)
    )
    fig.update_traces(marker_line_width=0, opacity=0.9)
    return fig

def chart_saldo_mensile(df):
    """Barre saldo netto per mese (verde = avanzo, rosso = disavanzo)."""
    d = df.copy()
    d["signed"] = d.apply(
        lambda r: r["importo"] if r["tipo"] == "Entrata" else -r["importo"], axis=1
    )
    ms = (d.groupby("mese")["signed"].sum()
           .reset_index()
           .sort_values("mese"))
    ms["mese_label"] = ms["mese"].map(MESI)
    ms["color"]      = ms["signed"].apply(lambda v: C_IN if v >= 0 else C_OUT)

    fig = go.Figure(go.Bar(
        x=ms["mese_label"],
        y=ms["signed"],
        marker_color=ms["color"],
        marker_line_width=0,
        opacity=0.88
    ))
    fig.update_layout(
        **BASE_LAYOUT,
        height=270,
        xaxis=dict(showgrid=False, color=C_MUT),
        yaxis=dict(tickprefix="€", gridcolor=C_BRD, color=C_MUT)
    )
    return fig

# ──────────────────────────────────────────────────────────────
#  SCHEDA KPI  (helper visuale)
# ──────────────────────────────────────────────────────────────
def kpi_card(col, label, value, color, sub=""):
    col.markdown(
        f"<div style='background:{C_S1}; border:1px solid {C_BRD}; border-radius:14px;"
        f"padding:1.2rem 1rem; text-align:center; border-top:3px solid {color};"
        f"box-shadow:0 2px 8px rgba(100,120,180,.07);'>"
        f"<div style='font-size:.68rem; font-weight:700; letter-spacing:1.5px;"
        f"color:{C_MUT}; text-transform:uppercase; margin-bottom:.3rem;'>{label}</div>"
        f"<div style='font-size:1.75rem; font-weight:700; color:{color};"
        f"font-family:\"JetBrains Mono\",monospace;'>{value}</div>"
        f"<div style='font-size:.72rem; color:{C_MUT}; margin-top:.2rem;'>{sub}</div>"
        f"</div>",
        unsafe_allow_html=True
    )

# ──────────────────────────────────────────────────────────────
#  PAGINA – DASHBOARD
# ──────────────────────────────────────────────────────────────
def page_dashboard(df_all, year):
    st.markdown(
        f"<h2 style='color:{C_TXT}; margin-bottom:1.2rem;'>"
        f"📊 Dashboard "
        f"<span style='font-size:1rem; font-weight:400; color:{C_MUT};'>{year}</span>"
        f"</h2>",
        unsafe_allow_html=True
    )

    if df_all.empty:
        st.info("📭 Nessuna transazione. Usa Nuova Voce per iniziare.")
        return

    df = df_all[df_all["anno"] == year]
    if df.empty:
        st.warning(f"Nessuna transazione per il {year}.")
        return

    rim     = get_rimanenza(df_all, year)
    tot_in  = df[df["tipo"] == "Entrata"]["importo"].sum()
    tot_out = df[df["tipo"] == "Uscita"]["importo"].sum()
    saldo   = rim + tot_in - tot_out
    n_in    = len(df[df["tipo"] == "Entrata"])
    n_out   = len(df[df["tipo"] == "Uscita"])

    # ── Rimanenza anno precedente ──
    rim_color = C_ACC
    st.markdown(
        f"<div style='background:{C_S1}; border:1px solid {C_BRD}; border-left:4px solid {C_ACC};"
        f"border-radius:12px; padding:.9rem 1.4rem; margin-bottom:1.2rem;"
        f"display:flex; justify-content:space-between; align-items:center;'>"
        f"<div>"
        f"<div style='font-size:.7rem; font-weight:700; letter-spacing:1px; color:{C_MUT};"
        f"text-transform:uppercase;'>Rimanenza anno precedente (automatica)</div>"
        f"<div style='font-size:.82rem; color:{C_MUT}; margin-top:.15rem;'>"
        f"Calcolata automaticamente — non richiede inserimento manuale</div>"
        f"</div>"
        f"<div style='font-size:1.6rem; font-weight:700; color:{C_ACC};"
        f"font-family:\"JetBrains Mono\",monospace;'>€{rim:,.2f}</div>"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── KPI ──
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "💚 Entrate",        f"€{tot_in:,.2f}",  C_IN,  f"{n_in} movimenti")
    kpi_card(c2, "❤️ Uscite",         f"€{tot_out:,.2f}", C_OUT, f"{n_out} movimenti")
    kpi_card(c3, "💙 Saldo effettivo", f"€{saldo:,.2f}",  C_IN if saldo >= 0 else C_OUT, "rimanenza inclusa")
    kpi_card(c4, "📌 Movimenti",       str(n_in + n_out), C_ACC, "transazioni totali")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Grafici riga 1 ──
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown(f"<h4 style='color:{C_TXT}; margin-bottom:.5rem;'>Entrate vs Uscite per mese</h4>",
                    unsafe_allow_html=True)
        st.plotly_chart(chart_barre_mensili(df), use_container_width=True)

    with col_b:
        st.markdown(f"<h4 style='color:{C_TXT}; margin-bottom:.5rem;'>Dove vanno le uscite</h4>",
                    unsafe_allow_html=True)
        fig_donut = chart_donut_uscite(df)
        if fig_donut:
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("Nessuna uscita registrata.")

    # ── Grafici riga 2 ──
    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown(f"<h4 style='color:{C_TXT}; margin-bottom:.5rem;'>Saldo cumulativo</h4>",
                    unsafe_allow_html=True)
        st.plotly_chart(chart_saldo_cumulativo(df, rim), use_container_width=True)

    with col_d:
        st.markdown(f"<h4 style='color:{C_TXT}; margin-bottom:.5rem;'>Uscite per categoria</h4>",
                    unsafe_allow_html=True)
        fig_cat = chart_uscite_per_categoria(df)
        if fig_cat:
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Nessuna uscita registrata.")

    st.markdown(f"<h4 style='color:{C_TXT}; margin-bottom:.5rem; margin-top:.5rem;'>Saldo netto per mese</h4>",
                unsafe_allow_html=True)
    st.plotly_chart(chart_saldo_mensile(df), use_container_width=True)

    # ── Ultime transazioni ──
    st.markdown(f"<h4 style='color:{C_TXT}; margin-top:.5rem; margin-bottom:.8rem;'>Ultime 10 transazioni</h4>",
                unsafe_allow_html=True)
    recent = df.sort_values("data", ascending=False).head(10)

    for _, r in recent.iterrows():
        color = C_IN  if r["tipo"] == "Entrata" else C_OUT
        sign  = "+"   if r["tipo"] == "Entrata" else "-"
        dot_col = color

        col_info, col_amt = st.columns([4, 1])
        with col_info:
            st.markdown(
                f"<div style='padding:.6rem .8rem; background:{C_S1}; border:1px solid {C_BRD};"
                f"border-left:4px solid {dot_col}; border-radius:8px;"
                f"box-shadow:0 1px 3px rgba(100,120,180,.05);'>"
                f"<span style='font-weight:600; color:{C_TXT};'>{r['descrizione']}</span>"
                f"<span style='color:{C_MUT}; font-size:.8rem; margin-left:.6rem;'>— {r['categoria']}</span>"
                f"<span style='color:{C_MUT}; font-size:.75rem; float:right;'>{r['data'].strftime('%d %b %Y')}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_amt:
            st.markdown(
                f"<div style='padding:.6rem .8rem; text-align:right;'>"
                f"<span style='color:{color}; font-weight:700; font-size:1.05rem;"
                f"font-family:\"JetBrains Mono\",monospace;'>{sign}€{r['importo']:,.2f}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

# ──────────────────────────────────────────────────────────────
#  PAGINA – TRANSAZIONI
# ──────────────────────────────────────────────────────────────
def page_transazioni(df_all, year):
    st.markdown(
        f"<h2 style='color:{C_TXT}; margin-bottom:1.2rem;'>"
        f"📋 Transazioni "
        f"<span style='font-size:1rem; font-weight:400; color:{C_MUT};'>{year}</span>"
        f"</h2>",
        unsafe_allow_html=True
    )

    if df_all.empty:
        st.info("📭 Nessuna transazione.")
        return

    df = df_all[df_all["anno"] == year].copy()
    if df.empty:
        st.warning(f"Nessuna transazione per il {year}.")
        return

    rim = get_rimanenza(df_all, year)

    # ── Riepilogo per categoria ──
    st.markdown(f"<h4 style='color:{C_TXT}; margin-bottom:.8rem;'>Riepilogo per categoria</h4>",
                unsafe_allow_html=True)

    entrate_cat = df[df["tipo"]=="Entrata"].groupby("categoria")["importo"].sum()
    uscite_cat  = df[df["tipo"]=="Uscita"].groupby("categoria")["importo"].sum()
    tot_in      = entrate_cat.sum()
    tot_out     = uscite_cat.sum()
    saldo_fin   = rim + tot_in - tot_out
    cs          = C_IN if saldo_fin >= 0 else C_OUT

    col_e, col_u = st.columns(2)

    with col_e:
        rows_e = ""
        rows_e += (
            f"<tr>"
            f"<td style='padding:.5rem .8rem; border-bottom:1px solid {C_BRD}; color:{C_MUT}; font-style:italic;'>"
            f"Rimanenza anno prec.</td>"
            f"<td style='padding:.5rem .8rem; border-bottom:1px solid {C_BRD}; text-align:right;"
            f"color:{C_ACC}; font-family:monospace; font-weight:700;'>€{rim:,.2f}</td>"
            f"</tr>"
        )
        for cat, val in entrate_cat.items():
            rows_e += (
                f"<tr>"
                f"<td style='padding:.5rem .8rem; border-bottom:1px solid {C_BRD}; color:{C_TXT};'>{cat}</td>"
                f"<td style='padding:.5rem .8rem; border-bottom:1px solid {C_BRD}; text-align:right;"
                f"color:{C_IN}; font-family:monospace; font-weight:700;'>+€{val:,.2f}</td>"
                f"</tr>"
            )
        rows_e += (
            f"<tr>"
            f"<td style='padding:.6rem .8rem; font-weight:700; color:{C_TXT};'>TOTALE DISPONIBILE</td>"
            f"<td style='padding:.6rem .8rem; text-align:right; font-weight:700;"
            f"color:{C_IN}; font-family:monospace;'>€{rim+tot_in:,.2f}</td>"
            f"</tr>"
        )
        st.markdown(
            f"<div style='background:{C_S1}; border:1px solid {C_BRD}; border-radius:12px;"
            f"padding:1rem; box-shadow:0 2px 6px rgba(100,120,180,.07);'>"
            f"<div style='font-size:.68rem; font-weight:700; letter-spacing:1px; color:{C_MUT};"
            f"text-transform:uppercase; margin-bottom:.6rem;'>💚 Entrate + Rimanenza</div>"
            f"<table style='width:100%; border-collapse:collapse; font-size:.87rem;'>"
            f"<thead><tr>"
            f"<th style='padding:.4rem .8rem; text-align:left; font-size:.65rem; font-weight:700;"
            f"letter-spacing:1px; text-transform:uppercase; color:{C_MUT}; border-bottom:2px solid {C_BRD};'>Categoria</th>"
            f"<th style='padding:.4rem .8rem; text-align:right; font-size:.65rem; font-weight:700;"
            f"letter-spacing:1px; text-transform:uppercase; color:{C_MUT}; border-bottom:2px solid {C_BRD};'>Importo</th>"
            f"</tr></thead>"
            f"<tbody>{rows_e}</tbody>"
            f"</table></div>",
            unsafe_allow_html=True
        )

    with col_u:
        rows_u = ""
        for cat, val in uscite_cat.items():
            rows_u += (
                f"<tr>"
                f"<td style='padding:.5rem .8rem; border-bottom:1px solid {C_BRD}; color:{C_TXT};'>{cat}</td>"
                f"<td style='padding:.5rem .8rem; border-bottom:1px solid {C_BRD}; text-align:right;"
                f"color:{C_OUT}; font-family:monospace; font-weight:700;'>-€{val:,.2f}</td>"
                f"</tr>"
            )
        rows_u += (
            f"<tr>"
            f"<td style='padding:.6rem .8rem; font-weight:700; color:{C_TXT};'>TOTALE USCITE</td>"
            f"<td style='padding:.6rem .8rem; text-align:right; font-weight:700;"
            f"color:{C_OUT}; font-family:monospace;'>-€{tot_out:,.2f}</td>"
            f"</tr>"
            f"<tr>"
            f"<td style='padding:.4rem .8rem; color:{C_MUT}; font-size:.8rem;'>Saldo netto finale</td>"
            f"<td style='padding:.4rem .8rem; text-align:right; font-weight:700;"
            f"color:{cs}; font-family:monospace;'>€{saldo_fin:,.2f}</td>"
            f"</tr>"
        )
        st.markdown(
            f"<div style='background:{C_S1}; border:1px solid {C_BRD}; border-radius:12px;"
            f"padding:1rem; box-shadow:0 2px 6px rgba(100,120,180,.07);'>"
            f"<div style='font-size:.68rem; font-weight:700; letter-spacing:1px; color:{C_MUT};"
            f"text-transform:uppercase; margin-bottom:.6rem;'>❤️ Uscite per categoria</div>"
            f"<table style='width:100%; border-collapse:collapse; font-size:.87rem;'>"
            f"<thead><tr>"
            f"<th style='padding:.4rem .8rem; text-align:left; font-size:.65rem; font-weight:700;"
            f"letter-spacing:1px; text-transform:uppercase; color:{C_MUT}; border-bottom:2px solid {C_BRD};'>Categoria</th>"
            f"<th style='padding:.4rem .8rem; text-align:right; font-size:.65rem; font-weight:700;"
            f"letter-spacing:1px; text-transform:uppercase; color:{C_MUT}; border-bottom:2px solid {C_BRD};'>Importo</th>"
            f"</tr></thead>"
            f"<tbody>{rows_u if rows_u else '<tr><td colspan=2 style=\"color:#718096; padding:.5rem .8rem;\">Nessuna uscita</td></tr>'}</tbody>"
            f"</table></div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # ── Filtri ──
    st.markdown(f"<h4 style='color:{C_TXT}; margin-bottom:.8rem;'>Lista movimenti</h4>",
                unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        f_tipo = st.multiselect("Tipo", ["Entrata","Uscita"], default=["Entrata","Uscita"])
    with c2:
        all_cats = sorted(df["categoria"].unique().tolist())
        f_cat = st.multiselect("Categoria", all_cats, default=all_cats)
    with c3:
        avail       = sorted(df["mese"].unique().tolist())
        mese_labels = [MESI[m] for m in avail]
        f_ml        = st.multiselect("Mese", mese_labels, default=mese_labels)
    with c4:
        search = st.text_input("🔍 Cerca", placeholder="es. bolletta…")

    rev    = {v: k for k, v in MESI.items()}
    f_mn   = [rev[m] for m in f_ml]
    mask   = df["tipo"].isin(f_tipo) & df["categoria"].isin(f_cat) & df["mese"].isin(f_mn)
    if search:
        mask &= df["descrizione"].str.contains(search, case=False, na=False)
    df_f = df[mask].sort_values("data", ascending=False)

    st.markdown(
        f"<p style='color:{C_MUT}; font-size:.85rem; margin-bottom:.8rem;'>"
        f"<b>{len(df_f)}</b> risultati &nbsp;·&nbsp;"
        f"<span style='color:{C_IN};'>+€{df_f[df_f['tipo']=='Entrata']['importo'].sum():,.2f}</span>"
        f"&nbsp;&nbsp;"
        f"<span style='color:{C_OUT};'>-€{df_f[df_f['tipo']=='Uscita']['importo'].sum():,.2f}</span>"
        f"</p>",
        unsafe_allow_html=True
    )

    # ── Lista con expander ──
    ep = can_edit()
    for _, r in df_f.iterrows():
        color = C_IN  if r["tipo"] == "Entrata" else C_OUT
        sign  = "+"   if r["tipo"] == "Entrata" else "-"
        ico   = "⬆️"  if r["tipo"] == "Entrata" else "⬇️"

        with st.expander(
            f"{ico}  {r['data'].strftime('%d/%m/%Y')}  ·  {r['descrizione']}  ·  {sign}€{r['importo']:,.2f}"
        ):
            cl, cr = st.columns([3, 1])
            with cl:
                st.write(f"**Tipo:** {r['tipo']}")
                st.write(f"**Categoria:** {r['categoria']}")
                st.write(f"**Importo:** {sign}€{r['importo']:,.2f}")
                st.write(f"**Data:** {r['data'].strftime('%d %B %Y')}")
                if r.get("note"):
                    st.write(f"**Note:** {r['note']}")
            with cr:
                if ep:
                    if st.button("✏️ Modifica", key=f"ed_{r['id']}"):
                        st.session_state.edit_id = int(r["id"])
                        st.rerun()
                    if st.button("🗑️ Elimina", key=f"del_{r['id']}", type="secondary"):
                        data = load_tx()
                        data = [t for t in data if t["id"] != int(r["id"])]
                        save_tx(data)
                        st.success("Eliminata.")
                        st.rerun()

    # ── Form modifica ──
    if "edit_id" in st.session_state and ep:
        data = load_tx()
        tx   = next((t for t in data if t["id"] == st.session_state.edit_id), None)
        if tx:
            st.divider()
            st.markdown(f"<h4 style='color:{C_TXT};'>✏️ Modifica transazione</h4>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                nt   = st.selectbox("Tipo", ["Entrata","Uscita"],
                                    index=0 if tx["tipo"]=="Entrata" else 1, key="e_tipo")
                cats = CAT_ENTRATA if nt=="Entrata" else CAT_USCITA
                cval = tx["categoria"]
                copts = cats + [cval] if cval not in cats else cats
                ncb  = st.selectbox("Categoria", copts, index=copts.index(cval), key="e_cat")
                ncc  = ""
                if ncb == "Altro":
                    ncc = st.text_input("Specifica categoria", key="e_cust")
                nc   = ncc.strip() if (ncb=="Altro" and ncc.strip()) else ncb
                nd   = st.text_input("Descrizione", value=tx["descrizione"], key="e_desc")
            with c2:
                ni   = st.number_input("Importo (€)", value=float(tx["importo"]),
                                       min_value=0.01, step=0.01, key="e_imp")
                ndt  = st.date_input("Data",
                                     value=datetime.strptime(tx["data"], "%Y-%m-%d").date(),
                                     key="e_data")
                nn   = st.text_area("Note", value=tx.get("note",""), key="e_note")
            ca, cb = st.columns(2)
            with ca:
                if st.button("💾 Salva modifiche", type="primary"):
                    for t in data:
                        if t["id"] == st.session_state.edit_id:
                            t.update(tipo=nt, categoria=nc, descrizione=nd,
                                     importo=round(ni,2), data=ndt.strftime("%Y-%m-%d"), note=nn)
                    save_tx(data)
                    del st.session_state.edit_id
                    st.success("Salvato!")
                    st.rerun()
            with cb:
                if st.button("Annulla"):
                    del st.session_state.edit_id
                    st.rerun()

# ──────────────────────────────────────────────────────────────
#  PAGINA – NUOVA VOCE
# ──────────────────────────────────────────────────────────────
def page_nuova_voce():
    st.markdown(f"<h2 style='color:{C_TXT};'>➕ Nuova Voce</h2>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        tipo     = st.selectbox("Tipo *", ["Uscita", "Entrata"])
        cats     = CAT_USCITA if tipo == "Uscita" else CAT_ENTRATA
        cat_base = st.selectbox("Categoria *", cats)
        cat_custom = ""
        if cat_base == "Altro":
            cat_custom = st.text_input("✏️ Nome categoria personalizzata *",
                                       placeholder="es. Riparazione auto…")
        categoria   = cat_custom.strip() if (cat_base=="Altro" and cat_custom.strip()) else cat_base
        descrizione = st.text_input("Descrizione *", placeholder="es. Bolletta ENEL marzo")

    with c2:
        importo  = st.number_input("Importo (€) *", min_value=0.01, step=0.01,
                                   format="%.2f", value=0.01)
        data_tx  = st.date_input("Data *", value=date.today())
        note     = st.text_area("Note (opzionale)", placeholder="Dettagli aggiuntivi…", height=100)

    # Anteprima live
    if descrizione.strip():
        color = C_IN  if tipo == "Entrata" else C_OUT
        sign  = "+"   if tipo == "Entrata" else "-"
        cat_d = categoria if categoria else "⚠️ specifica la categoria"
        st.markdown(
            f"<div style='background:{C_S2}; border-left:4px solid {color}; border-radius:12px;"
            f"padding:1.1rem 1.4rem; margin-top:.5rem; margin-bottom:1rem;'>"
            f"<div style='font-size:.68rem; font-weight:700; letter-spacing:1px; color:{C_MUT};"
            f"text-transform:uppercase; margin-bottom:.4rem;'>Anteprima</div>"
            f"<div style='font-size:1.1rem; font-weight:600; color:{C_TXT};'>{descrizione}</div>"
            f"<div style='font-size:.82rem; color:{C_MUT}; margin-bottom:.5rem;'>"
            f"{cat_d} · {data_tx.strftime('%d %B %Y')}</div>"
            f"<div style='font-size:1.8rem; font-weight:700; color:{color};"
            f"font-family:\"JetBrains Mono\",monospace;'>{sign}€{importo:,.2f}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    if st.button("💾 Aggiungi transazione", type="primary", use_container_width=True):
        if not descrizione.strip():
            st.error("La descrizione è obbligatoria.")
        elif cat_base == "Altro" and not cat_custom.strip():
            st.error("Specifica il nome della categoria.")
        else:
            data = load_tx()
            data.append({
                "id":           next_id(data),
                "tipo":         tipo,
                "categoria":    categoria,
                "descrizione":  descrizione.strip(),
                "importo":      round(importo, 2),
                "data":         data_tx.strftime("%Y-%m-%d"),
                "note":         note.strip(),
                "aggiunto_da":  st.session_state.username,
                "created_at":   datetime.now().isoformat(),
            })
            save_tx(data)
            sign = "+" if tipo == "Entrata" else "-"
            st.success(f"Aggiunta: {descrizione} · {sign}€{importo:,.2f}")
            st.balloons()

# ──────────────────────────────────────────────────────────────
#  PAGINA – UTENTI
# ──────────────────────────────────────────────────────────────
def page_utenti():
    st.markdown(f"<h2 style='color:{C_TXT};'>👥 Gestione Utenti</h2>", unsafe_allow_html=True)
    users = load_users()

    ROLE_DESC = {
        "admin":  "Accesso completo: legge, scrive e gestisce utenti.",
        "editor": "Può aggiungere e modificare transazioni, non gestisce utenti.",
        "viewer": "Solo lettura: vede dashboard e transazioni.",
    }

    st.markdown(f"<h4 style='color:{C_TXT};'>Utenti esistenti</h4>", unsafe_allow_html=True)
    for uname, info in users.items():
        role_label = info["role"].upper()
        with st.expander(f"👤  {info.get('display_name', uname)}  (@{uname})  —  {role_label}"):
            c1, c2 = st.columns(2)
            with c1:
                nd = st.text_input("Nome visualizzato",
                                   value=info.get("display_name", uname), key=f"dn_{uname}")
                nr = st.selectbox("Ruolo", ["admin","editor","viewer"],
                                  index=["admin","editor","viewer"].index(info["role"]),
                                  key=f"r_{uname}")
                st.caption(ROLE_DESC.get(nr, ""))
            with c2:
                np = st.text_input("Nuova password (vuoto = invariata)",
                                   type="password", key=f"p_{uname}")

            ca, cb = st.columns(2)
            with ca:
                if st.button("💾 Salva", key=f"s_{uname}", type="primary"):
                    users[uname]["display_name"] = nd
                    users[uname]["role"]         = nr
                    if np:
                        users[uname]["password"] = _hash(np)
                    save_users(users)
                    st.success("Aggiornato.")
                    st.rerun()
            with cb:
                if uname != st.session_state.username:
                    if st.button("🗑️ Elimina", key=f"x_{uname}", type="secondary"):
                        del users[uname]
                        save_users(users)
                        st.success(f"@{uname} eliminato.")
                        st.rerun()
                else:
                    st.caption("Non puoi eliminare te stesso.")

    st.divider()
    st.markdown(f"<h4 style='color:{C_TXT};'>Crea nuovo utente</h4>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        nu = st.text_input("Username *", placeholder="nome_utente")
        nn = st.text_input("Nome visualizzato", placeholder="Mario Rossi")
    with c2:
        np2 = st.text_input("Password *", type="password")
        nr2 = st.selectbox("Ruolo", ["viewer","editor","admin"])
    st.caption(ROLE_DESC.get(nr2, ""))

    if st.button("➕ Crea utente", type="primary"):
        if not nu or not np2:
            st.error("Username e password sono obbligatori.")
        elif nu in users:
            st.error("Username già esistente.")
        else:
            users[nu] = {"password": _hash(np2), "role": nr2, "display_name": nn or nu}
            save_users(users)
            st.success(f"Utente {nu} creato con ruolo {nr2}.")
            st.rerun()

# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────
def main():
    inject_css()
    require_auth()
    df_all = get_df()
    page, year = sidebar(df_all)

    if   page == "📊 Dashboard":   page_dashboard(df_all, year)
    elif page == "📋 Transazioni": page_transazioni(df_all, year)
    elif page == "➕ Nuova Voce":  page_nuova_voce()
    elif page == "👥 Utenti":      page_utenti()

if __name__ == "__main__":
    main()