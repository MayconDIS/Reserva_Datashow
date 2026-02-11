import sys
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import unicodedata
from datetime import datetime
import locale
import re 

# --- TENTA IMPORTAR A BIBLIOTECA PILLOW (PIL) ---
try:
    from PIL import Image as PILImage, ImageTk
except ImportError:
    messagebox.showerror("Erro", "Instale a biblioteca Pillow:\npip install Pillow")
    sys.exit()

# --- CONFIGURAÇÕES ---
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

try: locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
except:
    try: locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except: pass

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
except ImportError:
    messagebox.showerror("Erro", "Instale o reportlab:\npip install reportlab")
    sys.exit()

def get_resource_path(filename):
    if getattr(sys, 'frozen', False): base_path = os.path.dirname(sys.executable)
    else: base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

# --- DATABASE ---
def migrar_banco(cursor):
    try: cursor.execute("ALTER TABLE reservas ADD COLUMN contabilizada INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE equipe ADD COLUMN especialidade TEXT DEFAULT 'GERAL'")
    except sqlite3.OperationalError: pass

def init_db():
    db_path = get_resource_path('unip_sistema_v84_fix_layout.db') 
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS reservas (numero_linha INTEGER, periodo TEXT, professor TEXT, curso TEXT, bloco TEXT, horario_real TEXT, responsavel TEXT, responsavel_auditorio TEXT, contabilizada INTEGER DEFAULT 0, PRIMARY KEY (numero_linha, periodo))")
    cursor.execute("CREATE TABLE IF NOT EXISTS equipe (nome TEXT PRIMARY KEY, carga_acumulada INTEGER DEFAULT 0, disponivel INTEGER DEFAULT 1, especialidade TEXT DEFAULT 'GERAL')")
    cursor.execute("CREATE TABLE IF NOT EXISTS salas_turmas (id INTEGER PRIMARY KEY AUTOINCREMENT, curso_semestre TEXT UNIQUE, localizacao TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)")
    migrar_banco(cursor)
    
    cursor.execute("SELECT count(*) FROM equipe")
    if cursor.fetchone()[0] == 0:
        for nome, especialidade in EQUIPE_INICIAL:
            try: cursor.execute("INSERT INTO equipe (nome, carga_acumulada, disponivel, especialidade) VALUES (?, 0, 1, ?)", (nome, especialidade))
            except: pass 
    cursor.execute("SELECT count(*) FROM salas_turmas")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO salas_turmas (curso_semestre, localizacao) VALUES (?, ?)", SALAS_INICIAIS)
    conn.commit(); conn.close()

# --- VALIDATIONS ---
def verificar_conflito(num, periodo_novo):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    cursor = conn.cursor()
    msg_turno = "MANHÃ" if periodo_novo in ['M1', 'M2'] else "NOITE"
    cursor.execute("SELECT professor FROM reservas WHERE numero_linha = ? AND periodo = ?", (num, periodo_novo))
    res = cursor.fetchone(); conn.close()
    if res: return True, f"Linha {num} já ocupada de {msg_turno} ({periodo_novo}) por {res[0]}."
    return False, ""

# --- CRUD ---
def salvar_reserva(num, periodo, prof, curso, bloco, h_real, resp, resp_aud):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    conn.execute("INSERT OR REPLACE INTO reservas (numero_linha, periodo, professor, curso, bloco, horario_real, responsavel, responsavel_auditorio, contabilizada) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)", (num, periodo, prof, curso, bloco, h_real, resp, resp_aud))
    conn.commit(); conn.close()

def carregar_reservas():
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    res = conn.execute("SELECT * FROM reservas ORDER BY numero_linha").fetchall()
    conn.close(); return res

def get_equipe_completa():
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    res = conn.execute("SELECT nome, carga_acumulada, disponivel, especialidade FROM equipe ORDER BY nome ASC").fetchall()
    conn.close(); return res

def adicionar_membro_equipe(nome, especialidade="GERAL"):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    try: conn.execute("INSERT INTO equipe (nome, carga_acumulada, disponivel, especialidade) VALUES (?, 0, 1, ?)", (nome.upper(), especialidade)); conn.commit(); return True
    except: return False
    finally: conn.close()

def remover_membro_equipe(nome):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    conn.execute("DELETE FROM equipe WHERE nome = ?", (nome,)); conn.commit(); conn.close()

def get_todas_salas():
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    res = conn.execute("SELECT curso_semestre, localizacao FROM salas_turmas ORDER BY curso_semestre ASC").fetchall(); conn.close(); return res

def salvar_sala_manual(curso, local):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    conn.execute("INSERT OR REPLACE INTO salas_turmas (curso_semestre, localizacao) VALUES (?, ?)", (curso, local)); conn.commit(); conn.close()

def remover_sala_manual(curso):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    conn.execute("DELETE FROM salas_turmas WHERE curso_semestre = ?", (curso,)); conn.commit(); conn.close()

def buscar_local_por_curso(curso):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    res = conn.execute("SELECT localizacao FROM salas_turmas WHERE curso_semestre = ?", (curso,)).fetchone(); conn.close()
    return res[0] if res else None

def toggle_disponibilidade(nome, status_atual):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    novo = 0 if status_atual == 1 else 1
    conn.execute("UPDATE equipe SET disponivel = ? WHERE nome = ?", (novo, nome)); conn.commit(); conn.close()

def atualizar_carga_segura(nome, num_linha, periodo):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT contabilizada FROM reservas WHERE numero_linha = ? AND periodo = ?", (num_linha, periodo))
    res = cursor.fetchone()
    if res and res[0] == 0:
        cursor.execute("UPDATE equipe SET carga_acumulada = carga_acumulada + 1 WHERE nome = ?", (nome,))
        cursor.execute("UPDATE reservas SET contabilizada = 1 WHERE numero_linha = ? AND periodo = ?", (num_linha, periodo))
        conn.commit(); ret = True
    else: ret = False
    conn.close(); return ret

# --- INTELEGÊNCIA DE PROXIMIDADE ---
def extrair_info_bloco(texto_bloco):
    if not texto_bloco: return "", ""
    texto = texto_bloco.upper()
    letra = ""
    match_letra = re.search(r'([A-Z])\s*-', texto)
    if match_letra: letra = match_letra.group(1)
    andar = ""
    if "SUBSOLO" in texto: andar = "SUBSOLO"
    elif "TERREO" in texto or "TÉRREO" in texto: andar = "TERREO"
    elif "1º" in texto or "1°" in texto or "- 1 -" in texto: andar = "1"
    elif "2º" in texto or "2°" in texto or "- 2 -" in texto: andar = "2"
    return letra, andar

def calcular_penalidade_distancia(bloco_novo, blocos_existentes):
    if not blocos_existentes: return 0 
    letra_nova, andar_novo = extrair_info_bloco(bloco_novo)
    menor_penalidade = 100
    for b_existente in blocos_existentes:
        letra_exist, andar_exist = extrair_info_bloco(b_existente)
        penalidade = 100
        if letra_nova == letra_exist:
            if andar_novo == andar_exist: penalidade = 0 
            else: penalidade = 2 
        else: penalidade = 10 
        if penalidade < menor_penalidade: menor_penalidade = penalidade
    return menor_penalidade

def escolher_responsavel_inteligente(bloco_alvo):
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    equipe = conn.execute("SELECT nome, carga_acumulada, especialidade FROM equipe WHERE disponivel = 1").fetchall()
    if not equipe: conn.close(); return "SEM EQUIPE"
    reservas_hoje = conn.execute("SELECT responsavel, bloco FROM reservas").fetchall()
    conn.close()
    locais_responsavel = {m[0]: [] for m in equipe}
    carga_total = {m[0]: m[1] for m in equipe} 
    for r_resp, r_bloco in reservas_hoje:
        if r_resp in locais_responsavel:
            locais_responsavel[r_resp].append(r_bloco)
            carga_total[r_resp] += 1 
    candidatos = []
    especialistas_auditorio = []
    bloco_norm = remover_acentos(bloco_alvo)
    eh_auditorio = "AUDITORIO" in bloco_norm
    for nome, carga_hist, esp in equipe:
        if esp == "AUDITORIO": especialistas_auditorio.append(nome)
        penalidade_dist = calcular_penalidade_distancia(bloco_alvo, locais_responsavel[nome])
        score = (carga_total[nome] * 3) + penalidade_dist
        candidatos.append((nome, score))
    if eh_auditorio and especialistas_auditorio:
        melhor = sorted(especialistas_auditorio, key=lambda n: carga_total[n])[0]
        return melhor
    candidatos.sort(key=lambda x: x[1])
    return candidatos[0][0]

def verificar_novo_dia_e_limpar():
    conn = sqlite3.connect(get_resource_path('unip_sistema_v84_fix_layout.db'))
    cursor = conn.cursor()
    hoje = datetime.now().strftime("%d/%m/%Y")
    res = cursor.execute("SELECT valor FROM config WHERE chave='data_ultimo_uso'").fetchone()
    data_guardada = res[0] if res else None
    if data_guardada != hoje:
        cursor.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('data_ultimo_uso', ?)", (hoje,))
        conn.commit()
        if data_guardada and messagebox.askyesno("Novo Dia", f"Último uso: {data_guardada}.\nLimpar reservas anteriores?"):
            cursor.execute("DELETE FROM reservas"); conn.commit(); messagebox.showinfo("Limpeza", "Reservas limpas.")
    conn.close()

# --- PDF ---
def gerar_relatorio_pdf(data_cabecalho, mes_referencia, ano_referencia):
    try:
        try: parts = mes_referencia.upper().split(); mes_only = parts[0] if len(parts) >= 1 else "MES"
        except: mes_only = "MES"
        output_file = get_resource_path(f"Reserva_{mes_only}_{ano_referencia}.pdf")
        logo_file = get_resource_path("logo.png")
        doc = SimpleDocTemplate(output_file, pagesize=landscape(A4), rightMargin=2*mm, leftMargin=2*mm, topMargin=2*mm, bottomMargin=2*mm)
        elements = []
        if os.path.exists(logo_file):
            im = Image(logo_file, width=1.5*inch, height=0.4*inch)
            im.hAlign = 'LEFT' 
            elements.append(im); elements.append(Spacer(1, 2))
        styles = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle('TituloCenter', parent=styles['Normal'], fontSize=12, alignment=1, spaceAfter=0)
        data_formatada = f"{data_cabecalho} - {mes_referencia.upper()}/{ano_referencia}"
        
        reservas_raw = carregar_reservas() 
        linhas_dict = {i: [] for i in range(1, 21)}
        for r in reservas_raw:
            num = r[0]
            if num in linhas_dict: linhas_dict[num].append(r)
        lista_ordenada = []
        for num in range(1, 21):
            itens = linhas_dict[num]
            if itens: bloco_chave = itens[0][4] if itens[0][4] else "ZZZ"
            else: bloco_chave = "ZZZ"
            lista_ordenada.append((num, bloco_chave, itens))
        lista_ordenada.sort(key=lambda x: (x[1], x[0])) 
        
        texto_auditorio = "_______________"
        for r in reservas_raw:
            if len(r) > 7 and r[7] and r[7].strip(): texto_auditorio = r[7].strip().upper(); break
        texto_titulo = f"<b>RESERVA DE DATA SHOW | DIA: {data_formatada} | AUDITÓRIO: {texto_auditorio}</b>"
        elements.append(Paragraph(texto_titulo, estilo_titulo)); elements.append(Spacer(1, 5*mm)) 
        headers = ['Nº', 'HORA', 'PROFESSOR', 'CURSO', 'BLOCO', 'HORÁRIO', 'SOM/MIC', 'RESPONSÁVEL', 'Montou x Desmontou']
        data = [headers]
        tbl_style = [('GRID', (0,0), (-1,-1), 0.5, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 8), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('TOPPADDING', (0,0), (-1,-1), 1.8), ('BOTTOMPADDING', (0,0), (-1,-1), 1.8), ('LEFTPADDING', (0,0), (-1,-1), 1), ('RIGHTPADDING', (0,0), (-1,-1), 1), ('LEADING', (0,0), (-1,-1), 9)]
        str_som_mic = "SOM( ) MIC( )"; str_montou = "Montou( ) Desmontou( )"; row_idx = 1
        
        for num_original, bloco_ref, itens in lista_ordenada:
            def get_data(p_key):
                for item in itens:
                    if item[1] == p_key: 
                        resp = item[6] if item[6] else ""
                        if resp.strip(): atualizar_carga_segura(resp, item[0], item[1])
                        return [item[2], item[3], item[4], item[5], str_som_mic, resp, str_montou]
                return ["", "", "", "", str_som_mic, "", str_montou]
            tem_manha = any(i[1] in ['M1', 'M2'] for i in itens)
            p1 = 'M1' if tem_manha else '1'; p2 = 'M2' if tem_manha else '2'
            l1 = [str(num_original), "1º"] + get_data(p1); l2 = ["", "2º"] + get_data(p2)
            data.append(l1); data.append(l2); tbl_style.append(('SPAN', (0, row_idx), (0, row_idx+1))); row_idx += 2
        
        cw = [8*mm, 10*mm, 60*mm, 50*mm, 25*mm, 25*mm, 30*mm, 35*mm, 48*mm]
        t = Table(data, colWidths=cw, repeatRows=1); t.setStyle(TableStyle(tbl_style)); elements.append(t)
        doc.build(elements)
        if os.name == 'nt': os.startfile(output_file)
        messagebox.showinfo("Sucesso", "PDF Gerado (Ordenado por Bloco)!")
    except Exception as e: messagebox.showerror("Erro PDF", str(e))

# --- INTERFACE ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema UNIP - Gestão Centralizada (v8.4 Final Fixed)")
        self.geometry("700x600") 
        init_db()
        self.after(100, verificar_novo_dia_e_limpar)

        self.frm_nav = tk.Frame(self, bg="#f0f0f0", height=50); self.frm_nav.pack(side="top", fill="x")
        self.frm_nav_center = tk.Frame(self.frm_nav, bg="#f0f0f0"); self.frm_nav_center.pack(pady=10)
        
        btn_style = {"font": ("Arial", 10, "bold"), "relief": "raised", "bd": 2, "width": 18, "pady": 5}

        # --- BOTAO NOVA PAGINA ADICIONADO PRIMEIRO PARA FICAR NA ESQUERDA ---
        self.btn_nova_pagina = tk.Button(self.frm_nav_center, text="Nova Página", command=self.ao_clicar_nova_pagina, **btn_style)
        self.btn_nova_pagina.pack(side="left", padx=5)

        self.btn_reserva = tk.Button(self.frm_nav_center, text="Lançamento de Reservas", command=lambda: self.show_tab("reserva"), **btn_style); self.btn_reserva.pack(side="left", padx=5)
        self.btn_equipe = tk.Button(self.frm_nav_center, text="Equipe", command=lambda: self.show_tab("equipe"), **btn_style); self.btn_equipe.pack(side="left", padx=5)
        self.btn_salas = tk.Button(self.frm_nav_center, text="Gestão de Salas", command=lambda: self.show_tab("salas"), **btn_style); self.btn_salas.pack(side="left", padx=5)

        self.container = tk.Frame(self); self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1); self.container.grid_columnconfigure(0, weight=1)
        self.tab_reserva = tk.Frame(self.container); self.tab_equipe = tk.Frame(self.container); self.tab_salas = tk.Frame(self.container)
        for f in (self.tab_reserva, self.tab_equipe, self.tab_salas): f.grid(row=0, column=0, sticky="nsew")

        self.setup_reserva_tab(); self.setup_equipe_tab(); self.setup_salas_tab(); self.show_tab("reserva")

    def ao_clicar_nova_pagina(self):
        messagebox.showinfo("Nova Página", "Funcionalidade em desenvolvimento.")

    def show_tab(self, name):
        active_bg = "#4CAF50"; active_fg = "white"; inactive_bg = "#e1e1e1"; inactive_fg = "black"
        self.btn_nova_pagina.config(bg=inactive_bg, fg=inactive_fg)
        self.btn_reserva.config(bg=inactive_bg, fg=inactive_fg); self.btn_equipe.config(bg=inactive_bg, fg=inactive_fg); self.btn_salas.config(bg=inactive_bg, fg=inactive_fg)
        
        if name == "reserva": self.tab_reserva.tkraise(); self.btn_reserva.config(bg=active_bg, fg=active_fg)
        elif name == "equipe": self.tab_equipe.tkraise(); self.btn_equipe.config(bg=active_bg, fg=active_fg)
        elif name == "salas": self.tab_salas.tkraise(); self.btn_salas.config(bg=active_bg, fg=active_fg)

    def setup_reserva_tab(self):
        frame = self.tab_reserva
        frame.columnconfigure(0, weight=1, uniform="gp"); frame.columnconfigure(1, weight=1, uniform="gp"); frame.rowconfigure(0, weight=1)
        
        form_frame = tk.LabelFrame(frame, text="Nova Reserva", padx=10, pady=5)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        form_frame.columnconfigure(0, weight=1)
        tk.Label(form_frame, text="Período:", font=("Arial", 10, "bold"), fg="blue").grid(row=0, column=0, sticky="w", pady=(0, 2)) 
        p_frame = tk.Frame(form_frame); p_frame.grid(row=1, column=0, sticky="w", pady=(0, 5))
        self.combo_turno = ttk.Combobox(p_frame, values=["Diurno", "Noturno"], width=12, state="readonly"); self.combo_turno.set(""); self.combo_turno.pack(side="left", padx=(0, 15)); self.combo_turno.bind("<<ComboboxSelected>>", self.atualizar_combo_cursos)
        self.var_horario = tk.StringVar(value="1"); tk.Radiobutton(p_frame, text="1º Horário", variable=self.var_horario, value="1").pack(side="left", padx=5); tk.Radiobutton(p_frame, text="2º Horário", variable=self.var_horario, value="2").pack(side="left", padx=5)
        
        self.entries = {}; row_idx = 2; campos = [("Linha (1-20):", "num"), ("Professor:", "prof"), ("Curso/Semestre:", "curso_fake"), ("Bloco/Sala:", "bloco"), ("Horário:", "hreal"), ("Bedel Data:", "resp"), ("Bedel Auditório:", "audit")]
        self.placeholder_text = "Deixe vazio para Auto-Atribuir"
        for lbl, key in campos:
            tk.Label(form_frame, text=lbl, font=("Arial", 10)).grid(row=row_idx, column=0, sticky="w", pady=(2, 0)); row_idx += 1
            if key == "curso_fake": self.combo_curso = ttk.Combobox(form_frame); self.combo_curso.grid(row=row_idx, column=0, sticky="ew", pady=(0, 3)); self.combo_curso.bind("<<ComboboxSelected>>", self.autocompletar_local)
            elif key == "hreal": self.combo_hreal = ttk.Combobox(form_frame, values=["08:25 - 11:15", "17:55 - 20:25", "17:55 - 22:00", "19:10 - 20:25", "19:10 - 22:00", "20:25 - 22:00"]); self.combo_hreal.set(""); self.combo_hreal.grid(row=row_idx, column=0, sticky="ew", pady=(0, 3)); self.entries['hreal'] = self.combo_hreal
            elif key == "resp": e = tk.Entry(form_frame, fg='grey'); e.insert(0, self.placeholder_text); e.bind("<FocusIn>", lambda event, entry=e: self.on_entry_focus_in(entry)); e.bind("<FocusOut>", lambda event, entry=e: self.on_entry_focus_out(entry)); e.grid(row=row_idx, column=0, sticky="ew", pady=(0, 3)); self.entries[key] = e
            else: e = tk.Entry(form_frame); e.grid(row=row_idx, column=0, sticky="ew", pady=(0, 3)); self.entries[key] = e
            row_idx += 1
        tk.Button(form_frame, text="SALVAR RESERVA", bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), height=2, command=self.salvar).grid(row=row_idx, column=0, sticky="ew", pady=(15, 5))
        form_frame.rowconfigure(row_idx+1, weight=1) 

        right_panel = tk.Frame(frame); right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_panel.columnconfigure(0, weight=1); right_panel.rowconfigure(1, weight=1) 
        action_frame = tk.LabelFrame(right_panel, text="Relatório", padx=10, pady=5); action_frame.grid(row=0, column=0, sticky="ew")
        tk.Label(action_frame, text="Data (dd/mm/aaaa):").pack(anchor="w"); self.ent_data = tk.Entry(action_frame); self.ent_data.insert(0, datetime.now().strftime("%d/%m/%Y")); self.ent_data.pack(fill="x", pady=(0, 10))
        mes_atual = datetime.now().strftime("%B").upper(); tk.Label(action_frame, text="Mês Referência:").pack(anchor="w"); self.ent_mes = tk.Entry(action_frame); self.ent_mes.insert(0, mes_atual); self.ent_mes.pack(fill="x", pady=(0, 10))
        ano_atual = datetime.now().strftime("%Y"); tk.Label(action_frame, text="Ano Referência:").pack(anchor="w"); self.ent_ano = tk.Entry(action_frame); self.ent_ano.insert(0, ano_atual); self.ent_ano.pack(fill="x", pady=(0, 20))
        tk.Button(action_frame, text="GERAR PDF", bg="#2196F3", fg="white", font=("Arial", 10, "bold"), height=2, command=self.gerar).pack(fill="x")
        self.logo_frame = tk.LabelFrame(right_panel, text="Institucional", padx=10, pady=5); self.logo_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        logo_path = get_resource_path("logo.png")
        if os.path.exists(logo_path):
            try:
                self.original_pil_image = PILImage.open(logo_path); self.lbl_logo = tk.Label(self.logo_frame); self.lbl_logo.pack(expand=True, fill="both"); self.logo_frame.bind("<Configure>", self.resize_logo)
            except: pass
        self.atualizar_combo_cursos()

    def resize_logo(self, event):
        if event.width < 10 or event.height < 10: return
        img_w, img_h = self.original_pil_image.size; ratio = min(event.width/img_w, event.height/img_h)
        self.tk_image = ImageTk.PhotoImage(self.original_pil_image.resize((int(img_w*ratio), int(img_h*ratio)), PILImage.LANCZOS))
        self.lbl_logo.config(image=self.tk_image)

    def on_entry_focus_in(self, entry):
        if entry.get() == self.placeholder_text: entry.delete(0, tk.END); entry.config(fg='black')
    def on_entry_focus_out(self, entry):
        if entry.get() == "": entry.insert(0, self.placeholder_text); entry.config(fg='grey')

    # --- EQUIPE TAB (CORRIGIDA: COLUNAS AJUSTADAS) ---
    def setup_equipe_tab(self):
        frame = self.tab_equipe
        frame.columnconfigure(0, weight=1); frame.rowconfigure(1, weight=1)

        frame_top = tk.LabelFrame(frame, text="Gerenciar Membros", padx=10, pady=5)
        frame_top.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        frame_top.columnconfigure(5, weight=1)

        tk.Label(frame_top, text="Nome:").grid(row=0, column=0, padx=5, sticky="w")
        self.entry_equipe_novo = tk.Entry(frame_top, width=15); self.entry_equipe_novo.grid(row=0, column=1, padx=5, sticky="ew")
        
        tk.Label(frame_top, text="Especialidade:").grid(row=0, column=2, padx=5, sticky="w")
        self.combo_esp = ttk.Combobox(frame_top, values=["GERAL", "AUDITORIO", "LÍDER"], width=10, state="readonly")
        self.combo_esp.set(""); self.combo_esp.grid(row=0, column=3, padx=5, sticky="ew")
        
        tk.Button(frame_top, text="ADICIONAR", bg="#4CAF50", fg="white", command=self.add_equipe).grid(row=0, column=4, padx=10, sticky="ew")
        
        self.entry_filtro_equipe = tk.Entry(frame_top, width=15)
        self.entry_filtro_equipe.grid(row=0, column=5, padx=(15, 5), sticky="ew")
        self.entry_filtro_equipe.bind("<KeyRelease>", self.filtrar_equipe)
        
        tk.Button(frame_top, text="Pesquisar", bg="#2196F3", fg="white", command=self.filtrar_equipe).grid(row=0, column=6, padx=5, sticky="e")

        self.lista_eq = ttk.Treeview(frame, columns=("Nome", "Carga", "Status", "Especialidade"), show="headings", height=12)
        
        # --- AJUSTE DAS COLUNAS PARA CABER EM 700PX ---
        # Total Width precisa ser < 650 para não sumir
        self.lista_eq.column("Nome", width=180, anchor="center", stretch=True)
        self.lista_eq.column("Carga", width=80, anchor="center", stretch=True)
        self.lista_eq.column("Status", width=120, anchor="center", stretch=True)
        self.lista_eq.column("Especialidade", width=150, anchor="center", stretch=True)

        self.lista_eq.heading("Nome", text="Membro"); self.lista_eq.heading("Carga", text="Histórico")
        self.lista_eq.heading("Status", text="Disponibilidade"); self.lista_eq.heading("Especialidade", text="Especialidade")
        self.lista_eq.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        p_actions = tk.Frame(frame, pady=10); p_actions.grid(row=2, column=0)
        tk.Button(p_actions, text="Alternar Presença", bg="#FF9800", fg="white", command=self.mudar_status).pack(side="left", padx=10)
        tk.Button(p_actions, text="REMOVER SELECIONADO", bg="#F44336", fg="white", command=self.del_equipe).pack(side="left", padx=10)
        self.atualizar_lista_equipe()

    def filtrar_equipe(self, event=None):
        query = self.entry_filtro_equipe.get().upper()
        for i in self.lista_eq.get_children(): self.lista_eq.delete(i)
        for m in get_equipe_completa():
            if query in m[0].upper():
                st = "DISPONÍVEL" if m[2] == 1 else "AUSENTE"
                self.lista_eq.insert("", "end", values=(m[0], m[1], st, m[3]))

    def add_equipe(self):
        nome = self.entry_equipe_novo.get().strip()
        esp = self.combo_esp.get()
        if not nome: messagebox.showwarning("Atenção", "Digite um nome."); return
        if not esp: messagebox.showwarning("Atenção", "Selecione uma especialidade."); return
        if adicionar_membro_equipe(nome, esp): 
            self.atualizar_lista_equipe(); self.entry_equipe_novo.delete(0, tk.END); self.combo_esp.set("")
            messagebox.showinfo("Sucesso", "Membro adicionado!")
        else: messagebox.showwarning("Erro", "Nome já existe!")

    def del_equipe(self):
        if self.lista_eq.selection():
            if messagebox.askyesno("Confirmar", f"Remover {self.lista_eq.item(self.lista_eq.selection()[0])['values'][0]}?"): remover_membro_equipe(self.lista_eq.item(self.lista_eq.selection()[0])['values'][0]); self.atualizar_lista_equipe()

    # --- SALAS TAB ---
    def setup_salas_tab(self):
        frame = self.tab_salas
        frame.columnconfigure(0, weight=1); frame.rowconfigure(1, weight=1)

        frame_top = tk.LabelFrame(frame, text="Gerenciar Sala", padx=10, pady=5)
        frame_top.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        frame_top.columnconfigure(5, weight=1)

        tk.Label(frame_top, text="Curso:").grid(row=0, column=0, padx=5, sticky="w")
        self.entry_sala_curso = tk.Entry(frame_top, width=20); self.entry_sala_curso.grid(row=0, column=1, padx=5, sticky="ew")
        
        tk.Label(frame_top, text="Local:").grid(row=0, column=2, padx=5, sticky="w")
        self.entry_sala_local = tk.Entry(frame_top, width=15); self.entry_sala_local.grid(row=0, column=3, padx=5, sticky="ew")
        
        tk.Button(frame_top, text="SALVAR / ATUALIZAR", bg="#4CAF50", fg="white", command=self.salvar_sala).grid(row=0, column=4, padx=10, sticky="ew")

        self.entry_filtro_salas = tk.Entry(frame_top, width=15)
        self.entry_filtro_salas.grid(row=0, column=5, padx=(15, 5), sticky="ew") 
        self.entry_filtro_salas.bind("<KeyRelease>", self.filtrar_salas)
        
        tk.Button(frame_top, text="Pesquisar", bg="#2196F3", fg="white", command=self.filtrar_salas).grid(row=0, column=6, padx=5, sticky="e")

        self.tree_salas = ttk.Treeview(frame, columns=("Curso", "Local"), show="headings", height=15)
        self.tree_salas.column("Curso", width=300, stretch=True); self.tree_salas.column("Local", width=200, stretch=True) 
        self.tree_salas.heading("Curso", text="Curso / Semestre"); self.tree_salas.heading("Local", text="Localização Padrão")
        self.tree_salas.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.tree_salas.bind("<<TreeviewSelect>>", self.ao_selecionar_sala)
        
        tk.Button(frame, text="REMOVER SELECIONADO", bg="#F44336", fg="white", command=self.remover_sala).grid(row=2, column=0, pady=10)
        self.atualizar_lista_salas()

    def filtrar_salas(self, event=None):
        query = self.entry_filtro_salas.get().upper()
        for i in self.tree_salas.get_children(): self.tree_salas.delete(i)
        for c, l in get_todas_salas():
            if query in c.upper() or query in l.upper():
                self.tree_salas.insert("", "end", values=(c, l))

    def atualizar_combo_cursos(self, event=None):
        t = self.combo_turno.get(); ts = get_todas_salas(); f = []
        for c, l in ts:
            if not t or (t == "Diurno" and "MANHÃ" in c.upper()) or (t == "Noturno" and "NOITE" in c.upper()): f.append(c)
        self.combo_curso['values'] = f; self.combo_curso.set(''); 
        if 'bloco' in self.entries: self.entries['bloco'].delete(0, tk.END)
        self.combo_hreal['values'] = ["08:25 - 11:15"] if t == "Diurno" else ["17:55 - 20:25", "17:55 - 22:00", "19:10 - 20:25", "19:10 - 22:00", "20:25 - 22:00"]; self.combo_hreal.set('')

    def autocompletar_local(self, event):
        l = buscar_local_por_curso(self.combo_curso.get())
        if l: self.entries['bloco'].delete(0, tk.END); self.entries['bloco'].insert(0, l)

    def mudar_status(self):
        if self.lista_eq.selection(): toggle_disponibilidade(self.lista_eq.item(self.lista_eq.selection()[0])['values'][0], 1 if self.lista_eq.item(self.lista_eq.selection()[0])['values'][2] == "DISPONÍVEL" else 0); self.atualizar_lista_equipe()
    def atualizar_lista_equipe(self):
        self.entry_filtro_equipe.delete(0, tk.END); self.filtrar_equipe()
    def gerar(self): gerar_relatorio_pdf(self.ent_data.get(), self.ent_mes.get(), self.ent_ano.get()); self.atualizar_lista_equipe()
    def atualizar_lista_salas(self):
        self.entry_filtro_salas.delete(0, tk.END); self.filtrar_salas()
        self.atualizar_combo_cursos()
    def ao_selecionar_sala(self, event):
        if self.tree_salas.selection(): i = self.tree_salas.item(self.tree_salas.selection()[0]); self.entry_sala_curso.delete(0, tk.END); self.entry_sala_curso.insert(0, i['values'][0]); self.entry_sala_local.delete(0, tk.END); self.entry_sala_local.insert(0, i['values'][1])
    def salvar_sala(self):
        if self.entry_sala_curso.get() and self.entry_sala_local.get(): salvar_sala_manual(self.entry_sala_curso.get(), self.entry_sala_local.get()); self.atualizar_lista_salas(); self.entry_sala_curso.delete(0, tk.END); self.entry_sala_local.delete(0, tk.END); messagebox.showinfo("Sucesso", "Sala atualizada!")
    def remover_sala(self):
        if self.tree_salas.selection() and messagebox.askyesno("Confirmar", "Remover?"): remover_sala_manual(self.tree_salas.item(self.tree_salas.selection()[0])['values'][0]); self.atualizar_lista_salas()

    def salvar(self):
        try:
            num = int(self.entries['num'].get())
            if not 1 <= num <= 20: raise ValueError
            turno = self.combo_turno.get()
            if not turno: messagebox.showwarning("Erro", "Selecione o Turno"); return
            
            per = f"M{self.var_horario.get()}" if turno == "Diurno" else self.var_horario.get()
            oc, msg = verificar_conflito(num, per)
            if oc and not messagebox.askyesno("Conflito", f"{msg}\nSubstituir?"): return

            if not all([self.entries['prof'].get(), self.combo_curso.get(), self.entries['bloco'].get(), self.entries['hreal'].get()]):
                messagebox.showwarning("Erro", "Preencha todos os campos"); return

            resp = self.entries['resp'].get()
            if resp == self.placeholder_text: resp = ""
            msg_x = ""
            if not resp.strip():
                resp = escolher_responsavel_inteligente(self.entries['bloco'].get())
                msg_x = f"\n\n🤖 Bedel: {resp}"

            salvar_reserva(num, per, self.entries['prof'].get(), self.combo_curso.get(), self.entries['bloco'].get(), self.entries['hreal'].get(), resp, self.entries['audit'].get())
            messagebox.showinfo("Sucesso", f"Linha {num} Salva!{msg_x}")
            
            self.entries['prof'].delete(0, tk.END); self.combo_curso.set(''); self.entries['bloco'].delete(0, tk.END); self.entries['resp'].delete(0, tk.END); self.entries['resp'].insert(0, self.placeholder_text); self.entries['resp'].config(fg='grey'); self.entries['audit'].delete(0, tk.END); self.entries['num'].focus()
        except: messagebox.showerror("Erro", "Linha inválida (1-20)")

if __name__ == "__main__":
    app = App()
    app.mainloop()