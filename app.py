import streamlit as st
import psycopg2
import psycopg2.extras
import os
import time
import ast
import unicodedata
import requests
import base64
from datetime import datetime
from fpdf import FPDF
from PIL import Image

# --- CONFIGURAÇÕES GERAIS ---
os.makedirs("fotos", exist_ok=True)
os.makedirs("documentos", exist_ok=True)

st.set_page_config(page_title="MOV INCLUA", layout="wide", initial_sidebar_state="expanded")

# --- CHAVE DA API IMGBB ---
IMGBB_API_KEY = "6c3c7d7468bd08f226d25d7ccf956560"

# --- ADAPTADOR MÁGICO PARA O BANCO EM NUVEM (SUPABASE) ---
class DBWrapper:
    def __init__(self):
        self.conn = psycopg2.connect(
            host="aws-1-sa-east-1.pooler.supabase.com",
            port="6543",
            dbname="postgres",
            user="postgres.mgqcbdlvvfxairxkuqdt",
            password="Muvinclua2026"
        )
    
    def execute(self, query, params=None):
        # Transforma os dicionários do Postgres em um formato fácil de ler
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Traduz a linguagem antiga do SQLite (?) para a linguagem nova do Postgres (%s)
        query_traduzida = query.replace('?', '%s')
        cursor.execute(query_traduzida, params)
        return cursor

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

def get_db():
    return DBWrapper()

# --- ESTILO CLEAN ---
st.markdown("""
    <style>
    .stButton>button {
        background-color: #0d6efd;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton>button:hover { background-color: #0b5ed7; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .stError { border-left: 4px solid #dc3545; }
    </style>
""", unsafe_allow_html=True)

ARQUIVO_LOGO = "inclusao preto.jpeg"

# --- FUNÇÕES DE APOIO ---
def safe_str(valor):
    return valor if valor is not None else ""

def safe_list(valor):
    try: return ast.literal_eval(valor) if valor else []
    except: return []

def idx(opcoes, valor):
    return opcoes.index(valor) if valor in opcoes else 0

def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

def get_valid_defaults(saved_val, options):
    saved_list = safe_list(saved_val)
    valid = []
    for item in saved_list:
        if item in options:
            valid.append(item)
        else:
            for opt in options:
                if str(item).lower() in opt.lower():
                    valid.append(opt)
                    break
    return list(set(valid))

# --- UPLOAD PARA O IMGBB ---
def upload_foto_imgbb(foto_bytes):
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": base64.b64encode(foto_bytes).decode('utf-8')
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json()['data']['url']
    else:
        raise Exception(f"Erro ao conectar com ImgBB: {response.text}")

# --- FUNÇÕES DE PDF ---
def gerar_ficha_pdf(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="FICHA DA CRIANCA - MOV INCLUA", ln=True, align='C')
    pdf.line(10, 20, 200, 20)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="DADOS PESSOAIS", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 8, txt=f"Nome: {remover_acentos(dados['nome'])}", ln=True)
    pdf.cell(200, 8, txt=f"Nascimento: {dados['nascimento']}", ln=True)
    pdf.cell(200, 8, txt=f"Mae: {remover_acentos(dados['mae'])} | Pai: {remover_acentos(dados['pai'])}", ln=True)
    pdf.multi_cell(0, 8, txt=f"Endereco: {remover_acentos(dados['endereco'])}")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="RESUMO MEDICO/ANAMNESE", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 8, txt=f"Condicoes: {remover_acentos(dados['condicoes'])}")
    pdf.multi_cell(0, 8, txt=f"Comunicacao: {remover_acentos(dados['comunicacao'])}")
    if dados['aler_sn'] == 'Sim':
        pdf.multi_cell(0, 8, txt=f"ALERGIA: {remover_acentos(dados['aler_obs'])}")
    pdf.multi_cell(0, 8, txt=f"Ajuda em Crise: {remover_acentos(dados['comp_crise'])}")
    
    caminho_pdf = f"documentos/ficha_{dados['id']}.pdf"
    pdf.output(caminho_pdf)
    return caminho_pdf

def gerar_historico_pdf(nome_crianca, historico):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"RELATORIO DE CULTOS - {remover_acentos(nome_crianca)}", ln=True, align='C')
    pdf.line(10, 20, 200, 20)
    pdf.ln(10)
    
    if not historico:
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, txt="Nenhum registro de culto encontrado.", ln=True)
    else:
        for h in historico:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 8, txt=f"Data: {h['data']} | Culto: {remover_acentos(h['periodo'])} | Unidade: {remover_acentos(h['unidade'])}", ln=True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(200, 6, txt=f"Coordenador: {remover_acentos(h['coordenador'])} | Voluntario: {remover_acentos(h['voluntario'])}", ln=True)
            pdf.multi_cell(0, 6, txt=f"Relato: {remover_acentos(h['relato'])}")
            pdf.ln(5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
    caminho_pdf = f"documentos/historico_{int(time.time())}.pdf"
    pdf.output(caminho_pdf)
    return caminho_pdf

def gerar_pdf_culto(dados_culto):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="FICHA DE ACOMPANHAMENTO DE CULTO", ln=True, align='C')
    pdf.line(10, 20, 200, 20)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 8, txt=f"Crianca: {remover_acentos(dados_culto['nome'])}", ln=0)
    pdf.cell(100, 8, txt=f"Data: {dados_culto['data']}", ln=1)
    pdf.cell(100, 8, txt=f"Periodo: {remover_acentos(dados_culto['periodo'])}", ln=0)
    pdf.cell(100, 8, txt=f"Unidade: {remover_acentos(dados_culto['unidade'])}", ln=1)
    
    pdf.ln(5)
    pdf.cell(100, 8, txt=f"Coordenador(a): {remover_acentos(dados_culto['coordenador'])}", ln=0)
    pdf.cell(100, 8, txt=f"Voluntario(a): {remover_acentos(dados_culto['voluntario'])}", ln=1)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="RELATORIO DETALHADO", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 8, txt=remover_acentos(dados_culto['relato']))
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 8, txt=f"Visitante: {dados_culto['visitante']}", ln=True)
    
    pdf.ln(30)
    pdf.line(10, pdf.get_y(), 90, pdf.get_y())
    pdf.line(110, pdf.get_y(), 190, pdf.get_y())
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(90, 5, txt="Assinatura do Responsavel", ln=0, align='C')
    pdf.cell(100, 5, txt="Assinatura do Coordenador / Voluntario", ln=1, align='C')

    caminho_pdf = f"documentos/culto_individual_{int(time.time())}.pdf"
    pdf.output(caminho_pdf)
    return caminho_pdf

def gerar_pdf_relatorio_geral(registros, data_filtro, turno_filtro, unidade_filtro):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="RELATORIO GERAL DE CULTOS", ln=True, align='C')
    
    pdf.set_font("Arial", '', 10)
    txt_data = data_filtro if data_filtro else "Todas"
    pdf.cell(200, 10, txt=f"Filtros -> Data: {txt_data} | Turno: {turno_filtro} | Unidade: {unidade_filtro}", ln=True, align='C')
    
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)
    
    if not registros:
        pdf.cell(200, 10, txt="Nenhum registro encontrado.", ln=True)
    else:
        for r in registros:
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(200, 8, txt=f"Crianca: {remover_acentos(r['nome'])}", ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.cell(200, 6, txt=f"Data: {r['data']} | Turno: {remover_acentos(r['periodo'])} | Unidade: {remover_acentos(r['unidade'])}", ln=True)
            pdf.cell(200, 6, txt=f"Coord: {remover_acentos(r['coordenador'])} | Voluntario: {remover_acentos(r['voluntario'])}", ln=True)
            pdf.multi_cell(0, 6, txt=f"Relato: {remover_acentos(r['relato'])}")
            pdf.ln(3)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(3)

    caminho_pdf = f"documentos/relatorio_geral_{int(time.time())}.pdf"
    pdf.output(caminho_pdf)
    return caminho_pdf

# --- INICIALIZAÇÃO DO BANCO DE DADOS (AGORA NO POSTGRES) ---
def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS criancas (
        id SERIAL PRIMARY KEY,
        nome TEXT, nascimento TEXT, endereco TEXT, responsavel TEXT, tel_responsavel TEXT,
        mae TEXT, tel_mae TEXT, pai TEXT, tel_pai TEXT, foto TEXT, arquivo_laudo TEXT,
        rapida_diag TEXT, rapida_soc TEXT, rapida_soc_obs TEXT, rapida_com TEXT, rapida_com_obs TEXT,
        rapida_rest_sn TEXT, rapida_rest_qual TEXT, rapida_aler_sn TEXT, rapida_aler_qual TEXT,
        rapida_ativ TEXT, rapida_agita TEXT, rapida_acalma TEXT, rapida_adc TEXT,
        condicoes TEXT, nivel_suporte TEXT, diag_obs TEXT, possui_laudo TEXT,
        acomp_sn TEXT, acomp_qual TEXT, med_sn TEXT, med_qual TEXT, esc_sn TEXT, esc_qual TEXT,
        comunicacao TEXT, comu_ajuda TEXT,
        sens_sn TEXT, sens_quais TEXT, sens_expl TEXT, sens_estresse TEXT, sens_adapt TEXT, sens_pref TEXT,
        est_sn TEXT, est_obs TEXT, int_hab TEXT, int_brinq TEXT, int_criancas TEXT, int_suporte TEXT,
        auto_banh TEXT, auto_banh_obs TEXT, auto_alim TEXT, auto_alim_obs TEXT, aler_sn TEXT, aler_obs TEXT,
        comp_rotina TEXT, comp_estrategia TEXT, comp_ambientes TEXT, 
        comp_gat_sn TEXT, comp_gat_quais TEXT, comp_les_sn TEXT, comp_les_quais TEXT, comp_crise TEXT,
        info_adc TEXT)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS acompanhamentos (
        id SERIAL PRIMARY KEY,
        crianca_id INTEGER, data TEXT, periodo TEXT, unidade TEXT, 
        coordenador TEXT, voluntario TEXT, relato TEXT, visitante TEXT)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS supervisores (
        id SERIAL PRIMARY KEY, nome TEXT, usuario TEXT UNIQUE, senha TEXT)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS acessos (
        id SERIAL PRIMARY KEY, supervisor TEXT, data_hora TEXT)''')
    
    admin = conn.execute("SELECT * FROM supervisores WHERE usuario='admin'").fetchone()
    if not admin:
        conn.execute("INSERT INTO supervisores (nome, usuario, senha) VALUES (?,?,?)", ("Administrador","admin","Inclua2026"))
    
    conn.commit()
    conn.close()

init_db()

# --- LOGIN E RASTREIO DE ACESSO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        try:
            if os.path.exists(ARQUIVO_LOGO):
                st.image(Image.open(ARQUIVO_LOGO), width=250)
        except Exception as e:
            st.warning(f"Aviso: Logotipo '{ARQUIVO_LOGO}' não carregado.")
        
        st.title("🔐 MOV INCLUA - Acesso")
        
        conn = get_db()
        ultimo = conn.execute("SELECT supervisor, data_hora FROM acessos ORDER BY id DESC LIMIT 1").fetchone()
        conn.close()
        
        if ultimo:
            st.info(f"Último acesso: **{ultimo['supervisor']}** em {ultimo['data_hora']}")

        usuario_login = st.text_input("Usuário")
        senha_login = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema"):
            conn = get_db()
            user = conn.execute("SELECT * FROM supervisores WHERE usuario=? AND senha=?", (usuario_login, senha_login)).fetchone()
            if user:
                agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                conn.execute("INSERT INTO acessos (supervisor, data_hora) VALUES (?,?)", (user['nome'], agora))
                conn.commit()
                st.session_state.autenticado = True
                st.session_state.usuario = user['nome']
                st.rerun()
            else:
                st.error("Usuário ou Senha incorretos.")
            conn.close()
    st.stop()

# --- MENU LATERAL ---
try:
    if os.path.exists(ARQUIVO_LOGO):
        st.sidebar.image(Image.open(ARQUIVO_LOGO), width=180)
except: pass

st.sidebar.markdown(f"Bem-vindo(a), **{st.session_state.usuario}**")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navegação", [
    "📝 1. Cadastro Pessoal", 
    "⚡ 2. Ficha de Acolhimento Rápido",
    "🧠 3. Ficha de Acolhimento Completa", 
    "📋 4. Acompanhamento do Culto", 
    "🖨️ 5. Buscar & Imprimir",
    "👥 6. Gestão de Equipe"
])

# ==========================================
# ABA 1: CADASTRO PESSOAL
# ==========================================
if menu == "📝 1. Cadastro Pessoal":
    st.header("📝 Cadastro Pessoal")
    
    modo = st.radio("O que você deseja fazer?", ["✨ Novo Cadastro", "✏️ Editar Cadastro", "🗑️ Apagar Cadastro"], horizontal=True)
    st.divider()
    
    v_id = None
    v_nome, v_nasc, v_end, v_resp, v_tel_resp, v_mae, v_tel_mae, v_pai, v_tel_pai, v_foto_antiga = "", "", "", "", "", "", "", "", "", None
    
    if modo in ["✏️ Editar Cadastro", "🗑️ Apagar Cadastro"]:
        conn = get_db()
        lista_edit = conn.execute("SELECT id, nome, nascimento FROM criancas ORDER BY nome").fetchall()
        
        if lista_edit:
            opcoes_edit = {f"{c['nome']} (Nasc: {c['nascimento']})": c['id'] for c in lista_edit}
            selec_edit = st.selectbox("Selecione a Criança:", opcoes_edit.keys())
            v_id = opcoes_edit[selec_edit]
            
            if modo == "✏️ Editar Cadastro":
                dados = conn.execute("SELECT * FROM criancas WHERE id=?", (v_id,)).fetchone()
                v_nome, v_nasc, v_end = safe_str(dados['nome']), safe_str(dados['nascimento']), safe_str(dados['endereco'])
                v_resp, v_tel_resp = safe_str(dados['responsavel']), safe_str(dados['tel_responsavel'])
                v_mae, v_tel_mae = safe_str(dados['mae']), safe_str(dados['tel_mae'])
                v_pai, v_tel_pai = safe_str(dados['pai']), safe_str(dados['tel_pai'])
                v_foto_antiga = dados['foto']
                
            elif modo == "🗑️ Apagar Cadastro":
                st.warning(f"Você está prestes a apagar o cadastro de **{selec_edit}**.")
                st.error("⚠️ Atenção: Esta ação apagará todo o histórico desta criança. Não pode ser desfeito.")
                
                if st.checkbox("Sim, tenho certeza que desejo apagar os dados"):
                    if st.button("🗑️ Apagar Cadastro Definitivamente"):
                        conn.execute("DELETE FROM acompanhamentos WHERE crianca_id=?", (v_id,))
                        conn.execute("DELETE FROM criancas WHERE id=?", (v_id,))
                        conn.commit()
                        st.success("Cadastro apagado com sucesso! Atualizando tela...")
                        time.sleep(1.5)
                        st.rerun()
        else:
            st.info("Não há crianças cadastradas no momento.")
        conn.close()

    if modo in ["✨ Novo Cadastro", "✏️ Editar Cadastro"] and (modo == "✨ Novo Cadastro" or v_id is not None):
        with st.form("form_cad"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da Criança", value=v_nome)
            nasc = c2.text_input("Data de Nascimento (Ex: 10/05/2018)", value=v_nasc, max_chars=10)
            endereco = st.text_input("Endereço Completo", value=v_end)
            
            if v_foto_antiga:
                if str(v_foto_antiga).startswith('http'):
                    st.image(v_foto_antiga, width=150, caption="Foto na Nuvem")
                elif os.path.exists(v_foto_antiga):
                    st.image(v_foto_antiga, width=150, caption="Foto Local Antiga")
            
            st.markdown("📷 **Nova Foto da Criança** (Substitui a atual e salva na Nuvem)")
            foto_up = st.file_uploader("Anexar arquivo de imagem", type=['png', 'jpg', 'jpeg'])
            foto_cam = st.camera_input("Ou capturar foto na hora com a câmera")
            foto = foto_cam or foto_up
            
            st.subheader("Responsáveis e Contatos")
            r1, r2 = st.columns([2,1])
            responsavel = r1.text_input("Responsável Principal", value=v_resp)
            tel_responsavel = r2.text_input("Celular do Responsável", value=v_tel_resp)
            
            m, tm = st.columns([2,1])
            mae = m.text_input("Nome da Mãe", value=v_mae)
            tel_mae = tm.text_input("Celular (Mãe)", value=v_tel_mae)
            
            p, tp = st.columns([2,1])
            pai = p.text_input("Nome do Pai", value=v_pai)
            tel_pai = tp.text_input("Celular (Pai)", value=v_tel_pai)

            texto_botao = "💾 Salvar Novo Cadastro" if modo == "✨ Novo Cadastro" else "💾 Atualizar Cadastro"
            
            if st.form_submit_button(texto_botao):
                if not nome: 
                    st.error("O nome é obrigatório.")
                else:
                    f_path = v_foto_antiga
                    if foto:
                        st.info("🔄 Enviando a foto para a nuvem. Por favor, aguarde...")
                        try:
                            f_path = upload_foto_imgbb(foto.getvalue())
                        except Exception as e:
                            st.error(f"⚠️ Erro ao salvar foto: {e}")
                            st.stop()
                    
                    conn = get_db()
                    if modo == "✨ Novo Cadastro":
                        conn.execute('''INSERT INTO criancas (nome, nascimento, endereco, responsavel, tel_responsavel, mae, tel_mae, pai, tel_pai, foto) 
                                        VALUES (?,?,?,?,?,?,?,?,?,?)''', (nome, nasc, endereco, responsavel, tel_responsavel, mae, tel_mae, pai, tel_pai, f_path))
                        st.success("Criança cadastrada com sucesso!")
                    else:
                        conn.execute('''UPDATE criancas SET nome=?, nascimento=?, endereco=?, responsavel=?, tel_responsavel=?, 
                                        mae=?, tel_mae=?, pai=?, tel_pai=?, foto=? WHERE id=?''', 
                                     (nome, nasc, endereco, responsavel, tel_responsavel, mae, tel_mae, pai, tel_pai, f_path, v_id))
                        st.success("Cadastro atualizado!")
                    
                    conn.commit()
                    conn.close()
                    time.sleep(1.5)
                    st.rerun()

# ==========================================
# ABA 2: FICHA RÁPIDA
# ==========================================
elif menu == "⚡ 2. Ficha de Acolhimento Rápido":
    st.header("⚡ Ficha de Acolhimento Rápido")
    conn = get_db()
    lista = conn.execute("SELECT id, nome, nascimento FROM criancas ORDER BY nome").fetchall()
    
    if not lista: st.stop()
    opcoes = {f"{c['nome']} (Nasc: {c['nascimento']})": c['id'] for c in lista}
    selecionada = st.selectbox("Selecione a Criança:", opcoes.keys())
    id_crianca = opcoes[selecionada]
    
    dados = conn.execute("SELECT * FROM criancas WHERE id=?", (id_crianca,)).fetchone()
    opts_sn = ["Não", "Sim"]
    
    with st.form("form_rapida"):
        diag = st.text_area("Sobre a Necessidade Específica/Diagnóstico:", value=safe_str(dados['rapida_diag']))
        
        c1, c2 = st.columns(2)
        soc = c1.radio("1- A criança socializa bem com outras crianças?", opts_sn, index=idx(opts_sn, dados['rapida_soc']), horizontal=True)
        soc_obs = c1.text_input("Comente (Socialização):", value=safe_str(dados['rapida_soc_obs']))
        
        com = c2.radio("2- A criança se comunica de maneira funcional?", opts_sn, index=idx(opts_sn, dados['rapida_com']), horizontal=True)
        com_obs = c2.text_input("Comente (Comunicação):", value=safe_str(dados['rapida_com_obs']))
        
        c3, c4 = st.columns(2)
        rest = c3.radio("3- Restrição alimentar?", opts_sn, index=idx(opts_sn, dados['rapida_rest_sn']), horizontal=True)
        rest_qual = c3.text_input("Qual restrição?", value=safe_str(dados['rapida_rest_qual']))
        
        aler = c4.radio("4- Alergia?", opts_sn, index=idx(opts_sn, dados['rapida_aler_sn']), horizontal=True)
        aler_qual = c4.text_input("Qual alergia?", value=safe_str(dados['rapida_aler_qual']))
        
        ativ = st.text_input("5- Que tipo de atividade a criança gosta de fazer?", value=safe_str(dados['rapida_ativ']))
        agita = st.text_input("6- O que normalmente deixa a criança agitada?", value=safe_str(dados['rapida_agita']))
        acalma = st.text_input("7- O que normalmente ajuda essa criança a se acalmar?", value=safe_str(dados['rapida_acalma']))
        adc = st.text_area("8- O que mais você gostaria de nos contar sobre a criança?", value=safe_str(dados['rapida_adc']))
        
        if st.form_submit_button("Salvar Ficha Rápida"):
            conn.execute('''UPDATE criancas SET 
                            rapida_diag=?, rapida_soc=?, rapida_soc_obs=?, rapida_com=?, rapida_com_obs=?,
                            rapida_rest_sn=?, rapida_rest_qual=?, rapida_aler_sn=?, rapida_aler_qual=?,
                            rapida_ativ=?, rapida_agita=?, rapida_acalma=?, rapida_adc=? WHERE id=?''',
                         (diag, soc, soc_obs, com, com_obs, rest, rest_qual, aler, aler_qual, ativ, agita, acalma, adc, id_crianca))
            conn.commit()
            st.success("Ficha Rápida atualizada! Atualizando página...")
            time.sleep(1.5)
            st.rerun()
    conn.close()

# ==========================================
# ABA 3: FICHA DE ACOLHIMENTO COMPLETA
# ==========================================
elif menu == "🧠 3. Ficha de Acolhimento Completa":
    st.header("🧠 Ficha de Acolhimento Completa")
    conn = get_db()
    lista = conn.execute("SELECT id, nome, nascimento FROM criancas ORDER BY nome").fetchall()
    
    if not lista: st.stop()
    selecionada = st.selectbox("Selecione a Criança:", {f"{c['nome']} ({c['nascimento']})": c['id'] for c in lista}.keys())
    id_crianca = {f"{c['nome']} ({c['nascimento']})": c['id'] for c in lista}[selecionada]
    
    d = conn.execute("SELECT * FROM criancas WHERE id=?", (id_crianca,)).fetchone()
    opts_sn = ["Não", "Sim"]
    opts_ns_ns = ["Não sei", "Não", "Sim"]

    with st.form("form_anamnese"):
        st.markdown("### I - Sobre a Necessidade Especifica/Diagnóstico:")
        cond_ops = ["TEA - Transtorno Espectro Autista", "TDAH - Transtorno de Deficit de Atenção, Hiperatividade", 
                    "Down - Síndrome de Down", "DI - Deficiência Intelectual", "TOD - Transtorno Opositor Desafiador",
                    "TAG - Transtorno de Ansiedade Generalizada", "Deficiência Visual", "Deficiência Auditiva",
                    "PC - Paralísia Cerebral", "Outros"]
        conds = st.multiselect("1 - Sinalize todas as condições associadas", cond_ops, default=get_valid_defaults(d['condicoes'], cond_ops))
        
        nivel_ops = ["N/A", "1", "2", "3"]
        nivel = st.radio("Nível de Suporte (TEA):", nivel_ops, index=idx(nivel_ops, d['nivel_suporte']), horizontal=True)
        diag_obs = st.text_input("OBSERVAÇÃO:", value=safe_str(d['diag_obs']))
        
        laudo_med = st.text_input("2 - Possui laudo médico?", value=safe_str(d['possui_laudo']))
        
        c1, c2 = st.columns(2)
        acomp_sn = c1.radio("3 - Faz algum tipo de acompanhamento?", opts_sn, index=idx(opts_sn, d['acomp_sn']), horizontal=True)
        acomp_qual = c1.text_input("Qual?", value=safe_str(d['acomp_qual']))
        med_sn = c2.radio("4- Toma alguma medicação diariamente?", opts_sn, index=idx(opts_sn, d['med_sn']), horizontal=True)
        med_qual = c2.text_input("Qual é o medicamento?", value=safe_str(d['med_qual']))
        
        esc_sn = st.radio("5 - Frequenta escola regularmente?", opts_sn, index=idx(opts_sn, d['esc_sn']), horizontal=True)
        esc_qual = st.text_input("Qual nome da escola?", value=safe_str(d['esc_qual']))

        st.markdown("### II - COMUNICAÇÃO.")
        com_ops = ["Verbal - tem fala desenvolvida e compreensível", "Não verbal - Ausência de fala, palavras soltas, fala sem função (ecolalias)",
                   "Usa gesto para apontar e solicitar o que deseja", "Usa comunicação alternativa aumentativa CAA",
                   "Pistas Visuais o ajudam na compreensão.", "Tem dificuldade de compreensão quando é solicitado algo?"]
        comu = st.multiselect("1 - Como a criança se comunica?", com_ops, default=get_valid_defaults(d['comunicacao'], com_ops))
        comu_ajuda = st.text_input("2- Como podemos ajudá-lo em sua comunicação?", value=safe_str(d['comu_ajuda']))

        st.markdown("### III - QUESTÕES SENSORIAIS")
        sens_sn = st.radio("1 - Sua criança tem sensibilidades sensoriais?", opts_ns_ns, index=idx(opts_ns_ns, d['sens_sn']), horizontal=True)
        sens_ops = ["Luz - É sensível a muita claridade ou escuro?", "Som - É muito sensível ao barulho, como sons altos ou som especifico?",
                    "Toque - É sensível e ou não gosta de toques como abraço?", "Tato - Tem aversão com objetos pegajosos como massinha, mão suja?",
                    "Cheiro - Tem algum cheiro aversivo?", "Equilíbrio - tem dificuldades com mudanças de superfície, altura, pular, escalar?"]
        sens_quais = st.multiselect("2 - Quais são as mais relevantes?", sens_ops, default=get_valid_defaults(d['sens_quais'], sens_ops))
        sens_expl = st.text_input("4 - Explique melhor se necessário:", value=safe_str(d['sens_expl']))
        sens_est = st.text_area("5 - Como a criança reage a situações de estresse ou sobrecarga sensorial?", value=safe_str(d['sens_estresse']))
        sens_adapt = st.text_area("6 - Quais adaptações ou suportes seriam úteis?", value=safe_str(d['sens_adapt']))
        sens_pref = st.text_input("7 - A criança tem alguma preferência por algum ambiente?", value=safe_str(d['sens_pref']))

        st.markdown("### IV - ESTEREOTíPIAS.")
        est_sn = st.radio("1 - É agitado, anda e faz movimentos repetitivos?", opts_sn, index=idx(opts_sn, d['est_sn']), horizontal=True)
        est_obs = st.text_input("Se sim, quando elas acontecem? E como são?", value=safe_str(d['est_obs']))

        st.markdown("### V - INTERAÇÃO SOCIAL")
        int_hab = st.text_area("1 - Quais são as principais habilidades e interesses da criança?", value=safe_str(d['int_hab']))
        int_brinq = st.text_area("2 - Prefere brincar com quais brinquedos?", value=safe_str(d['int_brinq']))
        int_criancas = st.radio("3 - A criança gosta de interagir com outras crianças?", opts_sn, index=idx(opts_sn, d['int_criancas']), horizontal=True)
        int_suporte = st.text_input("Se sim, qual o suporte que precisa?", value=safe_str(d['int_suporte']))

        st.markdown("### VI - AUTONOMIA / INDEPENDÊNCIA")
        ca, cb = st.columns(2)
        auto_banh = ca.radio("A) Banheiro", opts_sn, index=idx(opts_sn, d['auto_banh']), horizontal=True)
        auto_banh_obs = ca.text_input("Qual suporte necessário? (Banheiro)", value=safe_str(d['auto_banh_obs']))
        
        auto_alim = cb.radio("B) Alimentação", opts_sn, index=idx(opts_sn, d['auto_alim']), horizontal=True)
        auto_alim_obs = cb.text_input("Qual suporte necessário? (Alimentação)", value=safe_str(d['auto_alim_obs']))
        
        aler_sn = st.radio("2 - Alguma alergia ou intolerância / restrição alimentar?", opts_sn, index=idx(opts_sn, d['aler_sn']), horizontal=True)
        aler_obs = st.text_input("Se sim, descreva:", value=safe_str(d['aler_obs']))

        st.markdown("### VII - COMPORTAMENTOS DESAFIADORES")
        comp_rotina = st.radio("1 - Sua criança se desorganiza com mudança de rotina?", opts_sn, index=idx(opts_sn, d['comp_rotina']), horizontal=True)
        comp_est = st.text_area("2 - A criança possui rotina para lidar com transições?", value=safe_str(d['comp_estrategia']))
        comp_amb = st.text_area("3 - Principais desafios em ambientes sociais?", value=safe_str(d['comp_ambientes']))
        
        gat_sn = st.radio("4 - Existe gatilho que pode levar a comportamentos desafiadores?", opts_sn, index=idx(opts_sn, d['comp_gat_sn']), horizontal=True)
        gat_quais = st.text_input("Se sim, quais?", value=safe_str(d['comp_gat_quais']), key="gatilhos_id")
        
        les_sn = st.radio("5 - A criança tem comportamentos autolesivos?", opts_sn, index=idx(opts_sn, d['comp_les_sn']), horizontal=True)
        les_quais = st.text_input("Se sim, quais?", value=safe_str(d['comp_les_quais']), key="lesoes_id")
        
        comp_crise = st.text_area("Em caso de crises, o que ajuda?", value=safe_str(d['comp_crise']))
        
        st.markdown("### VIII - Informações Adicionais")
        info_adc = st.text_area("Sugestão que você gostaria de compartilhar?", value=safe_str(d['info_adc']))

        if st.form_submit_button("Salvar Ficha Completa"):
            conn.execute('''UPDATE criancas SET 
                            condicoes=?, nivel_suporte=?, diag_obs=?, possui_laudo=?,
                            acomp_sn=?, acomp_qual=?, med_sn=?, med_qual=?, esc_sn=?, esc_qual=?,
                            comunicacao=?, comu_ajuda=?, sens_sn=?, sens_quais=?, sens_expl=?, sens_estresse=?, sens_adapt=?, sens_pref=?,
                            est_sn=?, est_obs=?, int_hab=?, int_brinq=?, int_criancas=?, int_suporte=?,
                            auto_banh=?, auto_banh_obs=?, auto_alim=?, auto_alim_obs=?, aler_sn=?, aler_obs=?,
                            comp_rotina=?, comp_estrategia=?, comp_ambientes=?, comp_gat_sn=?, comp_gat_quais=?, comp_les_sn=?, comp_les_quais=?, comp_crise=?,
                            info_adc=? WHERE id=?''',
                         (str(conds), nivel, diag_obs, laudo_med, acomp_sn, acomp_qual, med_sn, med_qual, esc_sn, esc_qual,
                          str(comu), comu_ajuda, sens_sn, str(sens_quais), sens_expl, sens_est, sens_adapt, sens_pref,
                          est_sn, est_obs, int_hab, int_brinq, int_criancas, int_suporte,
                          auto_banh, auto_banh_obs, auto_alim, auto_alim_obs, aler_sn, aler_obs,
                          comp_rotina, comp_est, comp_amb, gat_sn, gat_quais, les_sn, les_quais, comp_crise, info_adc, id_crianca))
            conn.commit()
            st.success("Ficha Completa atualizada com sucesso! Atualizando tela...")
            time.sleep(1.5)
            st.rerun()
    conn.close()

# ==========================================
# ABA 4: ACOMPANHAMENTO DO CULTO
# ==========================================
elif menu == "📋 4. Acompanhamento do Culto":
    st.header("📋 Acompanhamento do Culto")
    conn = get_db()
    lista = conn.execute("SELECT id, nome, nascimento FROM criancas ORDER BY nome").fetchall()
    
    if lista:
        opcoes = {f"{c['nome']} (Nasc: {c['nascimento']})": c['id'] for c in lista}
        nome_selecionado = st.selectbox("NOME DA CRIANÇA:", opcoes.keys())
        id_crianca = opcoes[nome_selecionado]
        nome_crianca_puro = nome_selecionado.split(" (")[0]
        
        data_digitada = st.text_input("DATA DO CULTO (Ex: 10/05/2026):", value=datetime.now().strftime("%d/%m/%Y"), max_chars=10)
        
        mes_str = data_digitada[3:] if len(data_digitada) == 10 else "/0000"
        ano_str = data_digitada[6:] if len(data_digitada) == 10 else "0000"
        
        f_dia = conn.execute("SELECT COUNT(*) FROM acompanhamentos WHERE crianca_id=? AND data=?", (id_crianca, data_digitada)).fetchone()['count']
        f_mes = conn.execute("SELECT COUNT(*) FROM acompanhamentos WHERE crianca_id=? AND data LIKE ?", (id_crianca, f"%{mes_str}%")).fetchone()['count']
        f_ano = conn.execute("SELECT COUNT(*) FROM acompanhamentos WHERE crianca_id=? AND data LIKE ?", (id_crianca, f"%{ano_str}%")).fetchone()['count']
        
        st.subheader("📈 Controle de Frequência")
        c_dia, c_mes, c_ano = st.columns(3)
        c_dia.metric(f"No Dia ({data_digitada[:5]})", f_dia)
        c_mes.metric("Neste Mês", f_mes)
        c_ano.metric("Neste Ano", f_ano)
        st.divider()

        with st.form("form_culto"):
            c1, c2 = st.columns(2)
            periodo = c1.selectbox("CULTO:", ["Manhã", "Noite"])
            unidade = c2.selectbox("UNIDADE:", ["CENTRO", "UTM"])
            
            coord_selecionado = st.selectbox("COORDENADOR(A):", ["ANA LILA", "JÚLIA", "LETHICIA", "LILIAN", "SARAH", "SUEIDE", "OUTROS"])
            coord_outro = st.text_input("Se escolheu 'OUTROS' acima, digite o nome do(a) novo(a) Coordenador(a) aqui:")
                
            voluntario = st.text_input("VOLUNTÁRIO(A):", value=st.session_state.usuario)
            relato = st.text_area("RELATÓRIO DETALHADO:")
            visitante = st.radio("VISITANTE?", ["NÃO", "SIM"], horizontal=True)
            
            if st.form_submit_button("💾 Salvar Acompanhamento"):
                coord_final = coord_outro.strip().upper() if coord_selecionado == "OUTROS" and coord_outro.strip() else coord_selecionado

                conn.execute('''INSERT INTO acompanhamentos (crianca_id, data, periodo, unidade, coordenador, voluntario, relato, visitante) 
                                VALUES (?,?,?,?,?,?,?,?)''', (id_crianca, data_digitada, periodo, unidade, coord_final, voluntario, relato, visitante))
                conn.commit()
                st.success("Relatório de culto salvo com sucesso no banco de dados!")
        
        coord_atual_display = coord_outro.strip().upper() if coord_selecionado == "OUTROS" and coord_outro.strip() else coord_selecionado
        
        dados_pdf_culto = {
            "nome": nome_crianca_puro, "data": data_digitada, "periodo": periodo, "unidade": unidade,
            "coordenador": coord_atual_display, "voluntario": voluntario, "relato": relato, "visitante": visitante
        }
        
        st.write("---")
        st.write("Para imprimir esta ficha de culto, clique abaixo:")
        pdf_path_culto = gerar_pdf_culto(dados_pdf_culto)
        with open(pdf_path_culto, "rb") as pdf_file:
            st.download_button(label="🖨️ Baixar Ficha do Culto em PDF", data=pdf_file, file_name=f"ficha_culto_{nome_crianca_puro}.pdf", mime="application/pdf")
            
    conn.close()

# ==========================================
# ABA 5: BUSCAR E IMPRIMIR
# ==========================================
elif menu == "🖨️ 5. Buscar & Imprimir":
    st.header("🖨️ Central de Consultas e Relatórios")
    
    tab_busca_ind, tab_relatorio_geral = st.tabs(["🔍 Busca Individual", "📊 Relatório Geral"])
    
    with tab_busca_ind:
        c1, c2 = st.columns(2)
        b_nome = c1.text_input("Nome da criança")
        b_data = c2.text_input("Data de Nascimento (Ex: 10/05/2018)")
        
        if st.button("Pesquisar"):
            conn = get_db()
            query = "SELECT * FROM criancas WHERE 1=1"
            params = []
            if b_nome: query += " AND nome LIKE ?"; params.append(f"%{b_nome}%")
            if b_data: query += " AND nascimento = ?"; params.append(b_data)
            res = conn.execute(query, params).fetchall()
            
            if res:
                for r in res:
                    with st.expander(f"👤 {safe_str(r['nome'])} (Nasc: {safe_str(r['nascimento'])})", expanded=True):
                        tab_dados, tab_rap, tab_ana, tab_hist, tab_docs = st.tabs(["📋 Dados", "⚡ Ficha Rápida", "🧠 Ficha Completa", "📜 Histórico", "🖨️ Imprimir"])
                        
                        with tab_dados:
                            c_img, c_inf = st.columns([1,2])
                            if r['foto']:
                                if str(r['foto']).startswith('http'):
                                    c_img.image(r['foto'], width=200, caption="Foto na Nuvem")
                                elif os.path.exists(r['foto']):
                                    c_img.image(r['foto'], width=200, caption="Foto Local")
                                    
                            c_inf.write(f"**Responsável:** {safe_str(r['responsavel'])} | **Cel:** {safe_str(r['tel_responsavel'])}")
                            c_inf.write(f"**Mãe:** {safe_str(r['mae'])} | **Pai:** {safe_str(r['pai'])}")
                            c_inf.write(f"**Endereço:** {safe_str(r['endereco'])}")
                            
                        with tab_rap:
                            st.write(f"**Diagnóstico:** {safe_str(r['rapida_diag'])}")
                            st.write(f"**Socializa?** {safe_str(r['rapida_soc'])} - {safe_str(r['rapida_soc_obs'])}")
                            
                        with tab_ana:
                            st.write(f"**Condições:** {safe_str(r['condicoes'])}")
                            st.write(f"**Comunicação:** {safe_str(r['comunicacao'])}")

                        with tab_hist:
                            historico = conn.execute("SELECT * FROM acompanhamentos WHERE crianca_id = ? ORDER BY id DESC", (r['id'],)).fetchall()
                            if historico:
                                for h in historico: st.info(f"📅 {h['data']} ({h['periodo']}) | Coord: {h['coordenador']} | Vol: {h['voluntario']}\n\n**Relato:** {h['relato']}")
                            else:
                                st.write("Sem registros de acompanhamento.")
                                
                        with tab_docs:
                            st.write("Selecione o documento:")
                            pdf_path_hist = gerar_historico_pdf(r['nome'], historico)
                            with open(pdf_path_hist, "rb") as pdf_file:
                                st.download_button(label="🖨️ Baixar Histórico de Cultos (PDF)", data=pdf_file, file_name=f"historico_{r['nome']}.pdf", mime="application/pdf", key=f"dl_hist_{r['id']}")
                            
                            pdf_path_ficha = gerar_ficha_pdf(r)
                            with open(pdf_path_ficha, "rb") as f:
                                st.download_button(label="🖨️ Baixar Ficha (PDF)", data=f, file_name=f"ficha_{r['nome']}.pdf", key=f"dl_ficha_{r['id']}")
            else:
                st.error("Criança não encontrada.")
            conn.close()

    with tab_relatorio_geral:
        st.subheader("Filtros para o Relatório")
        f_col1, f_col2, f_col3 = st.columns(3)
        r_data = f_col1.text_input("Filtrar por Data", placeholder="Ex: 10/05/2026")
        r_turno = f_col2.selectbox("Filtrar por Turno", ["Todos", "Manhã", "Noite"])
        r_unidade = f_col3.selectbox("Filtrar por Unidade", ["Todas", "CENTRO", "UTM"])
        
        if st.button("Gerar Relatório de Cultos", type="primary"):
            conn = get_db()
            query_rel = "SELECT a.data, a.periodo, a.unidade, a.coordenador, a.voluntario, a.relato, c.nome FROM acompanhamentos a JOIN criancas c ON a.crianca_id = c.id WHERE 1=1"
            params_rel = []
            
            if r_data:
                query_rel += " AND a.data = ?"
                params_rel.append(r_data)
            if r_turno != "Todos":
                query_rel += " AND a.periodo = ?"
                params_rel.append(r_turno)
            if r_unidade != "Todas":
                query_rel += " AND a.unidade = ?"
                params_rel.append(r_unidade)
                
            query_rel += " ORDER BY a.id DESC"
            res_rel = conn.execute(query_rel, params_rel).fetchall()
            
            if res_rel:
                st.success(f"Encontrado(s) {len(res_rel)} registro(s).")
                pdf_rel_geral = gerar_pdf_relatorio_geral(res_rel, r_data, r_turno, r_unidade)
                with open(pdf_rel_geral, "rb") as pdf_file:
                    st.download_button(label="🖨️ Baixar Relatório Geral (PDF)", data=pdf_file, file_name=f"rel_geral_{int(time.time())}.pdf", mime="application/pdf")
                
                st.write("---")
                for r in res_rel:
                    st.info(f"**Criança:** {safe_str(r['nome'])}\n\n**Data:** {r['data']} | **Turno:** {r['periodo']} | **Unidade:** {r['unidade']}\n\n**Coord:** {r['coordenador']} | **Voluntário:** {r['voluntario']}\n\n**Relato:** {r['relato']}")
            else:
                st.warning("Nenhum culto encontrado.")
            conn.close()

# ==========================================
# ABA 6: GESTÃO DE EQUIPE
# ==========================================
elif menu == "👥 6. Gestão de Equipe":
    st.header("👥 Cadastro de Supervisores")
    with st.form("form_user"):
        nome_sup = st.text_input("Nome Completo do Supervisor")
        user_sup = st.text_input("Login de Acesso (Ex: joao.silva)")
        senha_sup = st.text_input("Senha de Acesso")
        
        if st.form_submit_button("Cadastrar Supervisor"):
            if nome_sup and user_sup and senha_sup:
                try:
                    conn = get_db()
                    conn.execute("INSERT INTO supervisores (nome, usuario, senha) VALUES (?,?,?)", (nome_sup, user_sup, senha_sup))
                    conn.commit()
                    st.success(f"Supervisor '{nome_sup}' cadastrado!")
                except psycopg2.IntegrityError:
                    st.error("Erro: Esse 'Login' já está sendo usado.")
                finally:
                    conn.close()
            else:
                st.warning("Preencha todos os campos para cadastrar.")