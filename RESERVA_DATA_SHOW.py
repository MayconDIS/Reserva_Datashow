import sys
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import unicodedata
from datetime import datetime
import locale

# --- TENTA IMPORTAR A BIBLIOTECA PILLOW (PIL) PARA IMAGENS ---
try:
    from PIL import Image as PILImage, ImageTk
except ImportError:
    messagebox.showerror("Erro de Dependência", "Para que a logo funcione corretamente, você precisa instalar a biblioteca Pillow.\n\nAbra o terminal e digite: pip install Pillow")
    sys.exit()

# --- CONFIGURAÇÕES E CONSTANTES ---
EQUIPE_INICIAL = [
    ("MAYCON", "GERAL"), ("RAFAEL", "GERAL"), ("GABRIEL", "GERAL"), 
    ("DAVID", "GERAL"), ("FERNANDO", "GERAL"), ("MONTEIRO", "GERAL"), 
    ("RYAN", "GERAL"), ("JONATHAN", "AUDITORIO"), ("LUCAS", "GERAL"), ("EDUARDO", "GERAL")
]

SALAS_INICIAIS = [
    ("ADS 2º/3º A (Manhã)", "H - 2º - Sala 02"),
    ("CIÊN. COMP 2º/3º A (Manhã)", "H - 2º - Sala 04"),
    ("DIREITO 1º A (Manhã)", "F - 1º - Sala 04"),
    ("DIREITO 2º/3º A (Manhã)", "F - 1º - Sala 05"),
    ("DIREITO 4º/5º A (Manhã)", "F - 1º - Sala 03"),
    ("DIREITO 6º/7º A (Manhã)", "F - 1º - Sala 02"),
    ("DIREITO 8º/9º A (Manhã)", "F - 1º - Sala 01"),
    ("ESTÉTICA 2º/3º A (Manhã)", "F - Térreo - Sala 06"),
    ("VETERINÁRIA 2º/3º A (Manhã)", "H - 1º - Sala 02"),
    ("VETERINÁRIA 4º/5º A (Manhã)", "H - 1º - Sala 03"),
    ("VETERINÁRIA 6º/7º A (Manhã)", "H - 1º - Sala 04"),
    ("VETERINÁRIA 8º/9º A (Manhã)", "H - 1º - Sala 05"),
    ("VETERINÁRIA 10º (Manhã)", "H - 2º - Sala 05"),
    ("PSICOLOGIA 2º/3º A (Manhã)", "F - Térreo - Sala 02"),
    ("PSICOLOGIA 4º/5º A (Manhã)", "F - Térreo - Sala 03"),
    ("PSICOLOGIA 8º/9º A (Manhã)", "F - Térreo - Sala 04"),
    ("ADS 1º P (Noite)", "F - 1º - Sala 01"),
    ("ADS 2º P / 3º PQ (Noite)", "F - 1º - Sala 05"),
    ("ADS 4º PQ (Noite)", "F - 1º - Sala 02"),
    ("DESIGN GRÁFICO 1º P/4º P (Noite)", "D - 1º - Sala 06"),
    ("ADM 1º P (Noite)", "B - 2º - Sala 01"),
    ("DIREITO 1º (Noite)", "E - 1º - Sala 01"),
    ("ENFERMAGEM 2º/3º (Noite)", "E - 2º - Sala 05"),
    ("ENG. CIVIL 8º/9º (Noite)", "F - 1º - Sala 4")
]

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except:
        pass

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
except ImportError:
    messagebox.showerror("Erro", "Instale a biblioteca reportlab:\npip install reportlab")
    sys.exit()

# --- 1. CONFIGURAÇÃO ---
def get_resource_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

# --- 2. BANCO DE DADOS E MIGRAÇÃO ---
def migrar_banco(cursor):
    try: cursor.execute("ALTER TABLE reservas ADD COLUMN contabilizada INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE equipe ADD COLUMN especialidade TEXT DEFAULT 'GERAL'")
    except sqlite3.OperationalError: pass

def init_db():
    db_path = get_resource_path('unip_sistema_v71_fixed.db') 
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservas (
            numero_linha INTEGER,
            periodo TEXT, professor TEXT, curso TEXT, bloco TEXT, horario_real TEXT,
            responsavel TEXT, responsavel_auditorio TEXT, contabilizada INTEGER DEFAULT 0,
            PRIMARY KEY (numero_linha, periodo)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipe (
            nome TEXT PRIMARY KEY, carga_acumulada INTEGER DEFAULT 0,
            disponivel INTEGER DEFAULT 1, especialidade TEXT DEFAULT 'GERAL'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salas_turmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, curso_semestre TEXT UNIQUE, localizacao TEXT
        )
    """)
    migrar_banco(cursor)
    
    cursor.execute("SELECT count(*) FROM equipe")
    if cursor.fetchone()[0] == 0:
        for nome, especialidade in EQUIPE_INICIAL:
            try: cursor.execute("INSERT INTO equipe (nome, carga_acumulada, disponivel, especialidade) VALUES (?, 0, 1, ?)", (nome, especialidade))
            except sqlite3.IntegrityError: pass 

    cursor.execute("SELECT count(*) FROM salas_turmas")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO salas_turmas (curso_semestre, localizacao) VALUES (?, ?)", SALAS_INICIAIS)
            
    conn.commit()
    conn.close()

# --- VERIFICAR CONFLITO ---
def verificar_conflito(num, periodo_novo):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    cursor = conn.cursor()
    msg_turno = "MANHÃ" if periodo_novo in ['M1', 'M2'] else "NOITE"
    cursor.execute("SELECT professor FROM reservas WHERE numero_linha = ? AND periodo = ?", (num, periodo_novo))
    res = cursor.fetchone()
    conn.close()
    if res: return True, f"Linha {num} já ocupada de {msg_turno} ({periodo_novo}) por {res[0]}."
    return False, ""

# --- LÓGICA CRUD ---
def salvar_reserva(num, periodo, prof, curso, bloco, h_real, resp, resp_aud):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    conn.execute("INSERT OR REPLACE INTO reservas (numero_linha, periodo, professor, curso, bloco, horario_real, responsavel, responsavel_auditorio, contabilizada) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)", (num, periodo, prof, curso, bloco, h_real, resp, resp_aud))
    conn.commit()
    conn.close()

def carregar_reservas():
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reservas ORDER BY numero_linha")
    return cursor.fetchall()

def get_equipe_completa():
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    res = conn.execute("SELECT nome, carga_acumulada, disponivel, especialidade FROM equipe ORDER BY nome ASC").fetchall()
    conn.close()
    return res

def adicionar_membro_equipe(nome, especialidade="GERAL"):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    try:
        conn.execute("INSERT INTO equipe (nome, carga_acumulada, disponivel, especialidade) VALUES (?, 0, 1, ?)", (nome.upper(), especialidade))
        conn.commit()
        return True
    except sqlite3.IntegrityError: return False
    finally: conn.close()

def remover_membro_equipe(nome):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    conn.execute("DELETE FROM equipe WHERE nome = ?", (nome,))
    conn.commit()
    conn.close()

def get_todas_salas():
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    res = conn.execute("SELECT curso_semestre, localizacao FROM salas_turmas ORDER BY curso_semestre ASC").fetchall()
    conn.close()
    return res

def salvar_sala_manual(curso, local):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    conn.execute("INSERT OR REPLACE INTO salas_turmas (curso_semestre, localizacao) VALUES (?, ?)", (curso, local))
    conn.commit()
    conn.close()

def remover_sala_manual(curso):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    conn.execute("DELETE FROM salas_turmas WHERE curso_semestre = ?", (curso,))
    conn.commit()
    conn.close()

def buscar_local_por_curso(curso):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    res = conn.execute("SELECT localizacao FROM salas_turmas WHERE curso_semestre = ?", (curso,)).fetchone()
    conn.close()
    return res[0] if res else None

def toggle_disponibilidade(nome, status_atual):
    novo = 0 if status_atual == 1 else 1
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    conn.execute("UPDATE equipe SET disponivel = ? WHERE nome = ?", (novo, nome))
    conn.commit()
    conn.close()

def atualizar_carga_segura(nome, num_linha, periodo):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT contabilizada FROM reservas WHERE numero_linha = ? AND periodo = ?", (num_linha, periodo))
    res = cursor.fetchone()
    if res and res[0] == 0:
        cursor.execute("UPDATE equipe SET carga_acumulada = carga_acumulada + 1 WHERE nome = ?", (nome,))
        cursor.execute("UPDATE reservas SET contabilizada = 1 WHERE numero_linha = ? AND periodo = ?", (num_linha, periodo))
        conn.commit()
        retorno = True
    else: retorno = False
    conn.close()
    return retorno

def escolher_responsavel_inteligente(bloco):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v71_fixed.db'))
    equipe = conn.execute("SELECT nome, carga_acumulada, especialidade FROM equipe WHERE disponivel = 1").fetchall()
    if not equipe: conn.close(); return "SEM EQUIPE"
    reservas_hoje = conn.execute("SELECT responsavel FROM reservas").fetchall()
    conn.close()
    carga_total = {nome: carga_hist for nome, carga_hist, esp in equipe}
    for r in reservas_hoje:
        if r[0] in carga_total: carga_total[r[0]] += 1
    especialistas_auditorio = []
    for nome, carga, esp in equipe:
        if esp == "AUDITORIO": especialistas_auditorio.append(nome)
    bloco_norm = remover_acentos(bloco)
    if "AUDITORIO" in bloco_norm and especialistas_auditorio:
        melhor_especialista = sorted([(nome, carga_total[nome]) for nome in especialistas_auditorio], key=lambda x: x[1])[0]
        return melhor_especialista[0]
    equipe_list = [[nome, carga_total[nome]] for nome in carga_total]
    equipe_list.sort(key=lambda x: x[1])
    return equipe_list[0][0]

# --- PDF FINAL ---
def gerar_relatorio_pdf(data_cabecalho, mes_referencia, ano_referencia):
    try:
        try: parts = mes_referencia.upper().split(); mes_only = parts[0] if len(parts) >= 1 else "MES"
        except: mes_only = "MES"
        output_file = get_resource_path(f"Reserva_{mes_only}_{ano_referencia}.pdf")
        logo_file = get_resource_path("logo.png")
        doc = SimpleDocTemplate(output_file, pagesize=landscape(A4), rightMargin=2*mm, leftMargin=2*mm, topMargin=2*mm, bottomMargin=2*mm)
        elements = []
        if os.path.exists(logo_file):
            im = Image(logo_file, width=1.5*inch, height=0.4*inch); im.hAlign = 'CENTER'; elements.append(im); elements.append(Spacer(1, 2))
        styles = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle('TituloCenter', parent=styles['Normal'], fontSize=12, alignment=1, spaceAfter=0)
        data_formatada = f"{data_cabecalho} - {mes_referencia.upper()}/{ano_referencia}"
        reservas_raw = carregar_reservas()
        texto_auditorio = "_______________" 
        for r in reservas_raw:
            if len(r) > 7 and r[7] and r[7].strip(): texto_auditorio = r[7].strip().upper(); break
        texto_titulo = f"<b>RESERVA DE DATA SHOW | DIA: {data_formatada} | AUDITÓRIO: {texto_auditorio}</b>"
        elements.append(Paragraph(texto_titulo, estilo_titulo)); elements.append(Spacer(1, 5*mm)) 
        headers = ['Nº', 'HORA', 'PROFESSOR', 'CURSO', 'BLOCO', 'HORÁRIO', 'SOM/MIC', 'RESPONSÁVEL', 'Montou x Desmontou']
        data = [headers]
        mapa = {}
        for r in reservas_raw:
            if r[0] not in mapa: mapa[r[0]] = {}
            mapa[r[0]][r[1]] = r
        tbl_style = [('GRID', (0,0), (-1,-1), 0.5, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 8), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('TOPPADDING', (0,0), (-1,-1), 1.8), ('BOTTOMPADDING', (0,0), (-1,-1), 1.8), ('LEFTPADDING', (0,0), (-1,-1), 1), ('RIGHTPADDING', (0,0), (-1,-1), 1), ('LEADING', (0,0), (-1,-1), 9)]
        str_som_mic = "SOM( ) MIC( )"; str_montou = "Montou( ) Desmontou( )"; row_idx = 1
        for i in range(1, 21): 
            linha_data = mapa.get(i, {})
            def get_row_data(p_key):
                d = linha_data.get(p_key)
                if d:
                    resp_final = d[6] if d[6] else "" 
                    if d[6] and d[6].strip(): atualizar_carga_segura(d[6], d[0], d[1])
                    return [d[2], d[3], d[4], d[5], str_som_mic, resp_final, str_montou]
                return ["", "", "", "", str_som_mic, "", str_montou]
            if 'M1' in linha_data: top_data = get_row_data('M1'); top_row = [top_data[0]] + top_data[1:]
            elif '1' in linha_data: top_row = get_row_data('1')
            else: top_row = ["", "", "", "", str_som_mic, "", str_montou]
            if 'M2' in linha_data: btm_data = get_row_data('M2'); btm_row = [btm_data[0]] + btm_data[1:]
            elif '2' in linha_data: btm_row = get_row_data('2')
            else: btm_row = ["", "", "", "", str_som_mic, "", str_montou]
            l1 = [str(i), "1º"] + top_row; l2 = ["", "2º"] + btm_row
            data.append(l1); data.append(l2); tbl_style.append(('SPAN', (0, row_idx), (0, row_idx+1))); row_idx += 2
        cw = [8*mm, 10*mm, 60*mm, 50*mm, 25*mm, 25*mm, 30*mm, 35*mm, 48*mm]
        t = Table(data, colWidths=cw, repeatRows=1); t.setStyle(TableStyle(tbl_style)); elements.append(t)
        doc.build(elements)
        if os.name == 'nt': os.startfile(output_file)
        messagebox.showinfo("Sucesso", "PDF Gerado e Cargas Atualizadas!")
    except Exception as e: messagebox.showerror("Erro PDF", str(e))

# --- INTERFACE ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema UNIP - Gestão Centralizada (v7.1 Fixed)")
        self.geometry("800x600") 
        init_db()

        self.frm_nav = tk.Frame(self, bg="#f0f0f0", height=50)
        self.frm_nav.pack(side="top", fill="x")
        self.frm_nav_center = tk.Frame(self.frm_nav, bg="#f0f0f0")
        self.frm_nav_center.pack(pady=10)

        btn_style = {"font": ("Arial", 11, "bold"), "relief": "flat", "width": 20, "pady": 5}
        self.btn_reserva = tk.Button(self.frm_nav_center, text="Lançamento de Reservas", command=lambda: self.show_tab("reserva"), **btn_style)
        self.btn_reserva.pack(side="left", padx=5)
        self.btn_equipe = tk.Button(self.frm_nav_center, text="Equipe", command=lambda: self.show_tab("equipe"), **btn_style)
        self.btn_equipe.pack(side="left", padx=5)
        self.btn_salas = tk.Button(self.frm_nav_center, text="Gestão Manual de Salas", command=lambda: self.show_tab("salas"), **btn_style)
        self.btn_salas.pack(side="left", padx=5)

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.tab_reserva = tk.Frame(self.container)
        self.tab_equipe = tk.Frame(self.container)
        self.tab_salas = tk.Frame(self.container)

        for f in (self.tab_reserva, self.tab_equipe, self.tab_salas):
            f.grid(row=0, column=0, sticky="nsew")

        self.setup_reserva_tab()
        self.setup_equipe_tab()
        self.setup_salas_tab()
        self.show_tab("reserva")

    def show_tab(self, name):
        active_bg = "#4CAF50"; active_fg = "white"; inactive_bg = "#e1e1e1"; inactive_fg = "black"
        self.btn_reserva.config(bg=inactive_bg, fg=inactive_fg)
        self.btn_equipe.config(bg=inactive_bg, fg=inactive_fg)
        self.btn_salas.config(bg=inactive_bg, fg=inactive_fg)

        if name == "reserva": self.tab_reserva.tkraise(); self.btn_reserva.config(bg=active_bg, fg=active_fg)
        elif name == "equipe": self.tab_equipe.tkraise(); self.btn_equipe.config(bg=active_bg, fg=active_fg)
        elif name == "salas": self.tab_salas.tkraise(); self.btn_salas.config(bg=active_bg, fg=active_fg)

    def setup_reserva_tab(self):
        frame = self.tab_reserva
        frame.columnconfigure(0, weight=1, uniform="grupo_principal")
        frame.columnconfigure(1, weight=1, uniform="grupo_principal")
        frame.rowconfigure(0, weight=1)

        # === LADO ESQUERDO ===
        form_frame = tk.LabelFrame(frame, text="Nova Reserva", padx=15, pady=15)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        form_frame.columnconfigure(0, weight=1)

        tk.Label(form_frame, text="Período:", font=("Arial", 10, "bold"), fg="blue").grid(row=0, column=0, sticky="w", pady=(0, 2)) 
        p_frame = tk.Frame(form_frame)
        p_frame.grid(row=1, column=0, sticky="w", pady=(0, 5))
        self.combo_turno = ttk.Combobox(p_frame, values=["Diurno", "Noturno"], width=12, state="readonly")
        self.combo_turno.set(""); self.combo_turno.pack(side="left", padx=(0, 15))
        self.combo_turno.bind("<<ComboboxSelected>>", self.atualizar_combo_cursos)
        self.var_horario = tk.StringVar(value="1")
        tk.Radiobutton(p_frame, text="1º Horário", variable=self.var_horario, value="1").pack(side="left", padx=5)
        tk.Radiobutton(p_frame, text="2º Horário", variable=self.var_horario, value="2").pack(side="left", padx=5)

        self.entries = {}; row_idx = 2
        campos = [("Linha (1-20):", "num"), ("Professor:", "prof"), ("Curso/Semestre:", "curso_fake"), ("Bloco/Sala:", "bloco"), ("Horário:", "hreal"), ("Bedel Data:", "resp"), ("Bedel Auditório:", "audit")]
        self.placeholder_text = "Deixe vazio para Auto-Atribuir"

        for lbl, key in campos:
            tk.Label(form_frame, text=lbl, font=("Arial", 10)).grid(row=row_idx, column=0, sticky="w", pady=(2, 0)); row_idx += 1
            if key == "curso_fake":
                self.combo_curso = ttk.Combobox(form_frame)
                self.combo_curso.grid(row=row_idx, column=0, sticky="ew", pady=(0, 3))
                self.combo_curso.bind("<<ComboboxSelected>>", self.autocompletar_local)
            elif key == "hreal":
                self.combo_hreal = ttk.Combobox(form_frame, values=["08:25 - 11:15", "17:55 - 20:25", "17:55 - 22:00", "19:10 - 20:25", "19:10 - 22:00", "20:25 - 22:00"])
                self.combo_hreal.set("")
                self.combo_hreal.grid(row=row_idx, column=0, sticky="ew", pady=(0, 3))
                self.entries['hreal'] = self.combo_hreal
            elif key == "resp":
                e = tk.Entry(form_frame, fg='grey')
                e.insert(0, self.placeholder_text)
                e.bind("<FocusIn>", lambda event, entry=e: self.on_entry_focus_in(entry))
                e.bind("<FocusOut>", lambda event, entry=e: self.on_entry_focus_out(entry))
                e.grid(row=row_idx, column=0, sticky="ew", pady=(0, 3))
                self.entries[key] = e
            else:
                e = tk.Entry(form_frame)
                e.grid(row=row_idx, column=0, sticky="ew", pady=(0, 3))
                self.entries[key] = e
            row_idx += 1

        tk.Button(form_frame, text="SALVAR RESERVA", bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), height=2, command=self.salvar).grid(row=row_idx, column=0, sticky="ew", pady=(15, 5))
        form_frame.rowconfigure(row_idx+1, weight=1) 

        # === LADO DIREITO ===
        right_panel = tk.Frame(frame); right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        right_panel.columnconfigure(0, weight=1); right_panel.rowconfigure(1, weight=1) 

        # Relatório
        action_frame = tk.LabelFrame(right_panel, text="Relatório", padx=15, pady=15); action_frame.grid(row=0, column=0, sticky="ew")
        tk.Label(action_frame, text="Data (dd/mm/aaaa):").pack(anchor="w"); self.ent_data = tk.Entry(action_frame); self.ent_data.insert(0, datetime.now().strftime("%d/%m/%Y")); self.ent_data.pack(fill="x", pady=(0, 10))
        mes_atual = datetime.now().strftime("%B").upper(); tk.Label(action_frame, text="Mês Referência:").pack(anchor="w"); self.ent_mes = tk.Entry(action_frame); self.ent_mes.insert(0, mes_atual); self.ent_mes.pack(fill="x", pady=(0, 10))
        ano_atual = datetime.now().strftime("%Y"); tk.Label(action_frame, text="Ano Referência:").pack(anchor="w"); self.ent_ano = tk.Entry(action_frame); self.ent_ano.insert(0, ano_atual); self.ent_ano.pack(fill="x", pady=(0, 20))
        tk.Button(action_frame, text="GERAR PDF", bg="#2196F3", fg="white", font=("Arial", 10, "bold"), height=2, command=self.gerar).pack(fill="x")

        # Logo Institucional
        self.logo_frame = tk.LabelFrame(right_panel, text="Institucional", padx=10, pady=10)
        self.logo_frame.grid(row=1, column=0, sticky="nsew", pady=(20, 0))
        
        logo_path = get_resource_path("logo.png")
        if os.path.exists(logo_path):
            try:
                self.original_pil_image = PILImage.open(logo_path)
                self.lbl_logo = tk.Label(self.logo_frame)
                self.lbl_logo.pack(expand=True, fill="both")
                self.logo_frame.bind("<Configure>", self.resize_logo)
            except Exception as e:
                lbl_aviso = tk.Label(self.logo_frame, text=f"Erro imagem: {e}", fg="red"); lbl_aviso.pack(expand=True)
        else:
            lbl_aviso = tk.Label(self.logo_frame, text="UNIP\nSistema de Gestão", font=("Arial", 14, "bold"), fg="#cccccc"); lbl_aviso.pack(expand=True)

        self.atualizar_combo_cursos()

    def resize_logo(self, event):
        frame_width = event.width
        frame_height = event.height
        if frame_width < 10 or frame_height < 10: return
        img_width, img_height = self.original_pil_image.size
        ratio = min(frame_width / img_width, frame_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        resized_image = self.original_pil_image.resize((new_width, new_height), PILImage.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_image)
        self.lbl_logo.config(image=self.tk_image)

    def on_entry_focus_in(self, entry):
        if entry.get() == self.placeholder_text: entry.delete(0, tk.END); entry.config(fg='black')
    def on_entry_focus_out(self, entry):
        if entry.get() == "": entry.insert(0, self.placeholder_text); entry.config(fg='grey')

    # --- FUNÇÕES DESCOMPACTADAS (CORREÇÃO DE SINTAXE) ---
    def setup_equipe_tab(self):
        frame = self.tab_equipe
        p_add = tk.Frame(frame, pady=10)
        p_add.pack(fill="x", padx=40)
        tk.Label(p_add, text="Nome:").pack(side="left")
        self.entry_equipe_novo = tk.Entry(p_add, width=20)
        self.entry_equipe_novo.pack(side="left", padx=5)
        tk.Label(p_add, text="Especialidade:").pack(side="left")
        self.combo_esp = ttk.Combobox(p_add, values=["GERAL", "AUDITORIO"], width=12, state="readonly")
        self.combo_esp.set("GERAL")
        self.combo_esp.pack(side="left", padx=5)
        tk.Button(p_add, text="ADICIONAR", bg="#4CAF50", fg="white", command=self.add_equipe).pack(side="left")
        self.lista_eq = ttk.Treeview(frame, columns=("Nome", "Carga", "Status", "Especialidade"), show="headings", height=12)
        self.lista_eq.heading("Nome", text="Membro")
        self.lista_eq.heading("Carga", text="Histórico")
        self.lista_eq.heading("Status", text="Disponibilidade")
        self.lista_eq.heading("Especialidade", text="Especialidade")
        self.lista_eq.column("Nome", anchor="center")
        self.lista_eq.column("Carga", anchor="center")
        self.lista_eq.column("Status", anchor="center")
        self.lista_eq.column("Especialidade", anchor="center")
        self.lista_eq.pack(pady=10, fill="both", expand=True, padx=40)
        p_actions = tk.Frame(frame, pady=10)
        p_actions.pack()
        tk.Button(p_actions, text="Alternar Presença", bg="#FF9800", fg="white", command=self.mudar_status).pack(side="left", padx=10)
        tk.Button(p_actions, text="REMOVER SELECIONADO", bg="#F44336", fg="white", command=self.del_equipe).pack(side="left", padx=10)
        self.atualizar_lista_equipe()

    def add_equipe(self):
        nome = self.entry_equipe_novo.get().strip()
        esp = self.combo_esp.get()
        if nome:
            if adicionar_membro_equipe(nome, esp):
                self.atualizar_lista_equipe()
                self.entry_equipe_novo.delete(0, tk.END)
                messagebox.showinfo("Sucesso", "Membro adicionado!")
            else:
                messagebox.showwarning("Erro", "Nome já existe!")
        else:
            messagebox.showwarning("Atenção", "Digite um nome.")

    def del_equipe(self):
        sel = self.lista_eq.selection()
        if sel:
            nome = self.lista_eq.item(sel[0])['values'][0]
            if messagebox.askyesno("Confirmar", f"Remover {nome}?"):
                remover_membro_equipe(nome)
                self.atualizar_lista_equipe()

    def setup_salas_tab(self):
        frame = self.tab_salas
        p_add = tk.Frame(frame, pady=10)
        p_add.pack(fill="x", padx=40)
        tk.Label(p_add, text="Curso:").pack(side="left")
        self.entry_sala_curso = tk.Entry(p_add, width=25)
        self.entry_sala_curso.pack(side="left", padx=5)
        tk.Label(p_add, text="Local:").pack(side="left")
        self.entry_sala_local = tk.Entry(p_add, width=20)
        self.entry_sala_local.pack(side="left", padx=5)
        tk.Button(p_add, text="SALVAR / ATUALIZAR", bg="#4CAF50", fg="white", command=self.salvar_sala).pack(side="left", padx=10)
        self.tree_salas = ttk.Treeview(frame, columns=("Curso", "Local"), show="headings", height=15)
        self.tree_salas.heading("Curso", text="Curso / Semestre")
        self.tree_salas.heading("Local", text="Localização Padrão")
        self.tree_salas.column("Curso", width=300)
        self.tree_salas.column("Local", width=200)
        self.tree_salas.pack(fill="both", expand=True, padx=40, pady=10)
        self.tree_salas.bind("<<TreeviewSelect>>", self.ao_selecionar_sala)
        tk.Button(frame, text="REMOVER SELECIONADO", bg="#F44336", fg="white", command=self.remover_sala).pack(pady=10)
        self.atualizar_lista_salas()

    def atualizar_combo_cursos(self, event=None):
        turno_selecionado = self.combo_turno.get()
        todas_salas = get_todas_salas()
        lista_cursos_filtrada = []
        for curso, local in todas_salas:
            curso_upper = curso.upper()
            if not turno_selecionado:
                lista_cursos_filtrada.append(curso)
            elif turno_selecionado == "Diurno" and "MANHÃ" in curso_upper:
                lista_cursos_filtrada.append(curso)
            elif turno_selecionado == "Noturno" and "NOITE" in curso_upper:
                lista_cursos_filtrada.append(curso)
        self.combo_curso['values'] = lista_cursos_filtrada
        self.combo_curso.set('') 
        if 'bloco' in self.entries:
            self.entries['bloco'].delete(0, tk.END)
        horarios_manha = ["08:25 - 11:15"]
        horarios_noite = ["17:55 - 20:25", "17:55 - 22:00", "19:10 - 20:25", "19:10 - 22:00", "20:25 - 22:00"]
        if turno_selecionado == "Diurno":
            self.combo_hreal['values'] = horarios_manha
        elif turno_selecionado == "Noturno":
            self.combo_hreal['values'] = horarios_noite
        else:
            self.combo_hreal['values'] = horarios_manha + horarios_noite
        self.combo_hreal.set('') 

    def autocompletar_local(self, event):
        loc = buscar_local_por_curso(self.combo_curso.get())
        if loc:
            self.entries['bloco'].delete(0, tk.END)
            self.entries['bloco'].insert(0, loc)

    def mudar_status(self):
        sel = self.lista_eq.selection()
        if sel:
            nome = self.lista_eq.item(sel[0])['values'][0]
            st = self.lista_eq.item(sel[0])['values'][2]
            toggle_disponibilidade(nome, 1 if st == "DISPONÍVEL" else 0)
            self.atualizar_lista_equipe()

    def atualizar_lista_equipe(self):
        for i in self.lista_eq.get_children():
            self.lista_eq.delete(i)
        for m in get_equipe_completa():
            st = "DISPONÍVEL" if m[2] == 1 else "AUSENTE"
            self.lista_eq.insert("", "end", values=(m[0], m[1], st, m[3]))

    def gerar(self):
        gerar_relatorio_pdf(self.ent_data.get(), self.ent_mes.get(), self.ent_ano.get())
        self.atualizar_lista_equipe()

    def atualizar_lista_salas(self):
        for i in self.tree_salas.get_children():
            self.tree_salas.delete(i)
        for s in get_todas_salas():
            self.tree_salas.insert("", "end", values=s)
        self.atualizar_combo_cursos()

    def ao_selecionar_sala(self, event):
        sel = self.tree_salas.selection()
        if sel:
            item = self.tree_salas.item(sel[0])
            self.entry_sala_curso.delete(0, tk.END)
            self.entry_sala_curso.insert(0, item['values'][0])
            self.entry_sala_local.delete(0, tk.END)
            self.entry_sala_local.insert(0, item['values'][1])

    def salvar_sala(self):
        c = self.entry_sala_curso.get()
        l = self.entry_sala_local.get()
        if c and l:
            salvar_sala_manual(c, l)
            self.atualizar_lista_salas()
            self.entry_sala_curso.delete(0, tk.END)
            self.entry_sala_local.delete(0, tk.END)
            messagebox.showinfo("Sucesso", "Sala atualizada!")
        else:
            messagebox.showwarning("Atenção", "Preencha Curso e Local")

    def remover_sala(self):
        sel = self.tree_salas.selection()
        if sel: 
            if messagebox.askyesno("Confirmar", "Remover sala selecionada?"):
                remover_sala_manual(self.tree_salas.item(sel[0])['values'][0])
                self.atualizar_lista_salas()

    def salvar(self):
        try:
            num_str = self.entries['num'].get()
            if not num_str:
                raise ValueError
            num = int(num_str)
            if not 1 <= num <= 20:
                raise ValueError
            
            turno = self.combo_turno.get()
            if not turno:
                messagebox.showwarning("Atenção", "Selecione o Período (Noturno/Diurno).")
                return

            horario = self.var_horario.get()
            periodo_db = f"M{horario}" if turno == "Diurno" else horario
                
            ocupado, msg = verificar_conflito(num, periodo_db)
            if ocupado:
                if not messagebox.askyesno("Conflito", f"{msg}\nDeseja substituir?"):
                    return 
            
            prof = self.entries['prof'].get()
            curso = self.combo_curso.get()
            bloco = self.entries['bloco'].get()
            hreal = self.entries['hreal'].get()
            resp = self.entries['resp'].get()
            
            if resp == self.placeholder_text:
                resp = ""

            if not prof or not curso or not bloco or not hreal:
                messagebox.showwarning("Atenção", "Por favor, preencha todos os campos obrigatórios!")
                return

            resp_aud = self.entries['audit'].get()

            msg_extra = ""
            if not resp or resp.strip() == "":
                resp = escolher_responsavel_inteligente(bloco)
                msg_extra = f"\n\n🤖 Robô escalou Bedel Data: {resp}"

            salvar_reserva(num, periodo_db, prof, curso, bloco, hreal, resp, resp_aud)
            messagebox.showinfo("Sucesso", f"Linha {num} Salva!{msg_extra}")
            
            self.entries['prof'].delete(0, tk.END)
            self.combo_curso.set('')
            self.entries['bloco'].delete(0, tk.END)
            self.entries['resp'].delete(0, tk.END)
            self.entries['resp'].insert(0, self.placeholder_text)
            self.entries['resp'].config(fg='grey')
            self.entries['audit'].delete(0, tk.END)
            self.entries['num'].focus()
        except ValueError:
            messagebox.showerror("Erro", "Linha deve ser número entre 1 e 20")

if __name__ == "__main__":
    app = App()
    app.mainloop()