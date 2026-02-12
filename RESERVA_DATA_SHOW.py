"""
SISTEMA UNIP - GESTÃO CENTRALIZADA
Versão: 10.1 (Clean Code + Layout Fix)
Autor: Refatorado por IA (Gemini)
"""

import sys
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import unicodedata
from datetime import datetime
import locale
import re 

# --- TRATAMENTO DE DEPENDÊNCIAS EXTERNAS ---
try:
    from PIL import Image as PILImage, ImageTk
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
except ImportError as e:
    messagebox.showerror("Erro de Dependência", f"Biblioteca faltando: {e}\nInstale: pip install Pillow reportlab")
    sys.exit()

# --- CONSTANTES E CONFIGURAÇÕES ---
DB_NOME = 'unip_sistema_v10_clean.db'
TAMANHO_JANELA = "700x600"
TITULO_JANELA = "Sistema UNIP - Gestão Centralizada (v10.1 Layout Fix)"

# Paleta de Cores
COR_PRIMARIA = "#4CAF50"    # Verde
COR_SECUNDARIA = "#2196F3"  # Azul
COR_ALERTA = "#FF9800"      # Laranja
COR_PERIGO = "#F44336"      # Vermelho
COR_FUNDO = "#f0f0f0"       # Cinza Claro

# Dados Iniciais
EQUIPE_PADRAO = [
    ("MAYCON", "GERAL"), ("RAFAEL", "GERAL"), ("GABRIEL", "GERAL"), 
    ("DAVID", "GERAL"), ("FERNANDO", "GERAL"), ("MONTEIRO", "GERAL"), 
    ("RYAN", "GERAL"), ("JONATHAN", "AUDITÓRIO"), ("LUCAS", "GERAL"), ("EDUARDO", "GERAL")
]

SALAS_PADRAO = [
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

# Configuração de Localização
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
except:
    try: locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except: pass

# --- UTILITÁRIOS ---
class Utils:
    @staticmethod
    def obter_caminho_recurso(nome_arquivo):
        """Retorna o caminho absoluto do arquivo, compatível com PyInstaller."""
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, nome_arquivo)

    @staticmethod
    def remover_acentos(texto):
        if not texto: return ""
        return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

    @staticmethod
    def extrair_info_bloco(texto_bloco):
        """Extrai letra e andar do bloco para cálculo de distância."""
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

    @staticmethod
    def calcular_penalidade_distancia(bloco_novo, blocos_existentes):
        if not blocos_existentes: return 0 
        letra_nova, andar_novo = Utils.extrair_info_bloco(bloco_novo)
        menor_penalidade = 100
        for b_existente in blocos_existentes:
            letra_exist, andar_exist = Utils.extrair_info_bloco(b_existente)
            penalidade = 100
            if letra_nova == letra_exist:
                if andar_novo == andar_exist: penalidade = 0 
                else: penalidade = 2 
            else: penalidade = 10 
            if penalidade < menor_penalidade: menor_penalidade = penalidade
        return menor_penalidade

# --- CAMADA DE DADOS (REPOSITORY PATTERN) ---
class BancoDeDados:
    def __init__(self):
        self.caminho_db = Utils.obter_caminho_recurso(DB_NOME)
        self._inicializar_tabelas()

    def _conectar(self):
        return sqlite3.connect(self.caminho_db)

    def _inicializar_tabelas(self):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservas (
                numero_linha INTEGER, 
                periodo TEXT, 
                professor TEXT, 
                curso TEXT, 
                bloco TEXT, 
                horario_real TEXT, 
                responsavel TEXT, 
                responsavel_auditorio TEXT, 
                contabilizada INTEGER DEFAULT 0, 
                PRIMARY KEY (numero_linha, periodo)
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS equipe (nome TEXT PRIMARY KEY, carga_acumulada INTEGER DEFAULT 0, disponivel INTEGER DEFAULT 1, especialidade TEXT DEFAULT 'GERAL')")
        cursor.execute("CREATE TABLE IF NOT EXISTS salas_turmas (id INTEGER PRIMARY KEY AUTOINCREMENT, curso_semestre TEXT UNIQUE, localizacao TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)")
        
        # Migrações e Correções Automáticas
        try: cursor.execute("ALTER TABLE reservas ADD COLUMN contabilizada INTEGER DEFAULT 0")
        except: pass
        try: cursor.execute("ALTER TABLE equipe ADD COLUMN especialidade TEXT DEFAULT 'GERAL'")
        except: pass
        try: cursor.execute("UPDATE equipe SET especialidade = 'AUDITÓRIO' WHERE especialidade = 'AUDITORIO'")
        except: pass

        # Seed Inicial (se vazio)
        cursor.execute("SELECT count(*) FROM equipe")
        if cursor.fetchone()[0] == 0:
            for nome, esp in EQUIPE_PADRAO:
                try: cursor.execute("INSERT INTO equipe (nome, carga_acumulada, disponivel, especialidade) VALUES (?, 0, 1, ?)", (nome, esp))
                except: pass
        
        cursor.execute("SELECT count(*) FROM salas_turmas")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO salas_turmas (curso_semestre, localizacao) VALUES (?, ?)", SALAS_PADRAO)
            
        conn.commit()
        conn.close()

    # --- MÉTODOS DE RESERVAS ---
    def buscar_conflito_reserva(self, linha, periodo):
        conn = self._conectar()
        res = conn.execute("SELECT professor FROM reservas WHERE numero_linha = ? AND periodo = ?", (linha, periodo)).fetchone()
        conn.close()
        return res[0] if res else None

    def salvar_reserva(self, dados):
        conn = self._conectar()
        conn.execute("""
            INSERT OR REPLACE INTO reservas 
            (numero_linha, periodo, professor, curso, bloco, horario_real, responsavel, responsavel_auditorio, contabilizada) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, dados)
        conn.commit()
        conn.close()

    def listar_todas_reservas(self):
        conn = self._conectar()
        res = conn.execute("SELECT * FROM reservas ORDER BY numero_linha").fetchall()
        conn.close()
        return res

    def limpar_todas_reservas(self):
        conn = self._conectar()
        conn.execute("DELETE FROM reservas")
        conn.commit()
        conn.close()

    # --- MÉTODOS DE EQUIPE ---
    def listar_equipe(self):
        conn = self._conectar()
        res = conn.execute("SELECT nome, carga_acumulada, disponivel, especialidade FROM equipe ORDER BY nome ASC").fetchall()
        conn.close()
        return res

    def adicionar_membro(self, nome, especialidade):
        conn = self._conectar()
        try:
            conn.execute("INSERT INTO equipe (nome, carga_acumulada, disponivel, especialidade) VALUES (?, 0, 1, ?)", (nome.upper(), especialidade))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    def remover_membro(self, nome):
        conn = self._conectar()
        conn.execute("DELETE FROM equipe WHERE nome = ?", (nome,))
        conn.commit()
        conn.close()

    def alternar_disponibilidade(self, nome, status_atual_str):
        novo_status = 0 if status_atual_str == "DISPONÍVEL" else 1
        conn = self._conectar()
        conn.execute("UPDATE equipe SET disponivel = ? WHERE nome = ?", (novo_status, nome))
        conn.commit()
        conn.close()

    def incrementar_carga(self, nome, linha, periodo):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT contabilizada FROM reservas WHERE numero_linha = ? AND periodo = ?", (linha, periodo))
        res = cursor.fetchone()
        sucesso = False
        if res and res[0] == 0:
            cursor.execute("UPDATE equipe SET carga_acumulada = carga_acumulada + 1 WHERE nome = ?", (nome,))
            cursor.execute("UPDATE reservas SET contabilizada = 1 WHERE numero_linha = ? AND periodo = ?", (linha, periodo))
            conn.commit()
            sucesso = True
        conn.close()
        return sucesso

    # --- MÉTODOS DE SALAS ---
    def listar_salas(self):
        conn = self._conectar()
        res = conn.execute("SELECT curso_semestre, localizacao FROM salas_turmas ORDER BY curso_semestre ASC").fetchall()
        conn.close()
        return res

    def salvar_sala(self, curso, local):
        conn = self._conectar()
        conn.execute("INSERT OR REPLACE INTO salas_turmas (curso_semestre, localizacao) VALUES (?, ?)", (curso, local))
        conn.commit()
        conn.close()

    def remover_sala(self, curso):
        conn = self._conectar()
        conn.execute("DELETE FROM salas_turmas WHERE curso_semestre = ?", (curso,))
        conn.commit()
        conn.close()

    def buscar_local_sala(self, curso):
        conn = self._conectar()
        res = conn.execute("SELECT localizacao FROM salas_turmas WHERE curso_semestre = ?", (curso,)).fetchone()
        conn.close()
        return res[0] if res else None

    # --- CONFIGURAÇÃO ---
    def obter_config(self, chave):
        conn = self._conectar()
        res = conn.execute("SELECT valor FROM config WHERE chave = ?", (chave,)).fetchone()
        conn.close()
        return res[0] if res else None

    def salvar_config(self, chave, valor):
        conn = self._conectar()
        conn.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)", (chave, valor))
        conn.commit()
        conn.close()

# --- LÓGICA DE NEGÓCIO (SERVICES) ---
class BedelService:
    def __init__(self, db: BancoDeDados):
        self.db = db

    def escolher_responsavel_inteligente(self, bloco_alvo):
        """Algoritmo para escolher o melhor bedel baseado em carga e distância."""
        equipe = self.db.listar_equipe()
        equipe_disponivel = [m for m in equipe if m[2] == 1] # Index 2 é disponivel
        
        if not equipe_disponivel: return "SEM EQUIPE"

        # Carregar contexto do dia
        reservas_hoje = self.db.listar_todas_reservas()
        
        # Mapear locais atuais de cada bedel
        locais_responsavel = {m[0]: [] for m in equipe_disponivel}
        carga_atual = {m[0]: m[1] for m in equipe_disponivel} # Index 1 é carga

        for r in reservas_hoje:
            resp = r[6] # Index 6 é responsável
            bloco = r[4] # Index 4 é bloco
            if resp in locais_responsavel:
                locais_responsavel[resp].append(bloco)
                carga_atual[resp] += 1 # Simula carga do dia corrente

        candidatos = []
        especialistas_auditorio = []
        
        bloco_norm = Utils.remover_acentos(bloco_alvo)
        eh_auditorio = "AUDITORIO" in bloco_norm

        for nome, _, _, esp in equipe_disponivel: # Index 3 é especialidade
            if esp == "AUDITÓRIO": especialistas_auditorio.append(nome)
            
            penalidade_dist = Utils.calcular_penalidade_distancia(bloco_alvo, locais_responsavel[nome])
            # Fórmula: (Carga * 3) + Distancia. Menor score ganha.
            score = (carga_atual[nome] * 3) + penalidade_dist
            candidatos.append((nome, score))

        # Regra de Especialista
        if eh_auditorio and especialistas_auditorio:
            # Pega o especialista com menor carga
            melhor = sorted(especialistas_auditorio, key=lambda n: carga_atual[n])[0]
            return melhor

        # Ordena por menor score
        candidatos.sort(key=lambda x: x[1])
        return candidatos[0][0]

class RelatorioService:
    def __init__(self, db: BancoDeDados):
        self.db = db

    def gerar_pdf(self, data_cabecalho, mes_referencia, ano_referencia):
        try:
            # Nome do arquivo
            try: mes_safe = mes_referencia.upper().split()[0]
            except: mes_safe = "MES"
            output_file = Utils.obter_caminho_recurso(f"Reserva_{mes_safe}_{ano_referencia}.pdf")
            
            logo_path = Utils.obter_caminho_recurso("logo.png")
            
            # Layout A4 Paisagem com margens ajustadas
            doc = SimpleDocTemplate(output_file, pagesize=landscape(A4), 
                                    rightMargin=5*mm, leftMargin=5*mm, 
                                    topMargin=5*mm, bottomMargin=5*mm)
            elements = []
            
            # Logo
            if os.path.exists(logo_path):
                im = Image(logo_path, width=1.5*inch, height=0.4*inch)
                im.hAlign = 'CENTER' # Centralizado
                elements.append(im)
                elements.append(Spacer(1, 1*mm))
            
            # Título
            styles = getSampleStyleSheet()
            estilo_titulo = ParagraphStyle('TituloCenter', parent=styles['Normal'], fontSize=12, alignment=1)
            
            # Busca Auditorio se houver
            reservas = self.db.listar_todas_reservas()
            texto_auditorio = "_______________"
            for r in reservas:
                if len(r) > 7 and r[7] and r[7].strip():
                    texto_auditorio = r[7].strip().upper()
                    break
            
            titulo = f"<b>RESERVA DE DATA SHOW | DIA: {data_cabecalho} - {mes_referencia.upper()}/{ano_referencia} | AUDITÓRIO: {texto_auditorio}</b>"
            elements.append(Paragraph(titulo, estilo_titulo))
            elements.append(Spacer(1, 3*mm))
            
            # Preparar Dados da Tabela
            # Agrupar linhas para ordenar
            linhas_dict = {i: [] for i in range(1, 21)}
            for r in reservas:
                linhas_dict[r[0]].append(r)
            
            lista_ordenada = []
            for num in range(1, 21):
                itens = linhas_dict[num]
                bloco_chave = itens[0][4] if itens and itens[0][4] else "ZZZ"
                lista_ordenada.append((num, bloco_chave, itens))
            
            lista_ordenada.sort(key=lambda x: (x[1], x[0]))
            
            headers = ['Nº', 'HORA', 'PROFESSOR', 'CURSO', 'BLOCO', 'HORÁRIO', 'SOM/MIC', 'RESPONSÁVEL', 'Montou x Desmontou']
            data_tabela = [headers]
            
            # Estilo da Tabela Otimizado
            tbl_style = [
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TOPPADDING', (0,0), (-1,-1), 1.6), 
                ('BOTTOMPADDING', (0,0), (-1,-1), 1.6),
                ('LEFTPADDING', (0,0), (-1,-1), 1),
                ('RIGHTPADDING', (0,0), (-1,-1), 1),
                ('LEADING', (0,0), (-1,-1), 9), 
            ]
            
            str_som = "SOM( ) MIC( )"
            str_montou = "Montou( ) Desmontou( )"
            row_idx = 1
            
            for num_linha, _, itens_linha in lista_ordenada:
                def extrair(periodo_key):
                    for item in itens_linha:
                        if item[1] == periodo_key:
                            resp = item[6] if item[6] else ""
                            if resp.strip(): self.db.incrementar_carga(resp, item[0], item[1])
                            return [item[2], item[3], item[4], item[5], str_som, resp, str_montou]
                    return ["", "", "", "", str_som, "", str_montou]

                # Detecta se é manhã ou noite pelo ID do periodo
                tem_manha = any(i[1] in ['M1', 'M2'] for i in itens_linha)
                p1 = 'M1' if tem_manha else '1'
                p2 = 'M2' if tem_manha else '2'
                
                linha1 = [str(num_linha), "1º"] + extrair(p1)
                linha2 = ["", "2º"] + extrair(p2)
                
                data_tabela.append(linha1)
                data_tabela.append(linha2)
                tbl_style.append(('SPAN', (0, row_idx), (0, row_idx+1)))
                row_idx += 2
            
            # Larguras otimizadas para 287mm
            col_widths = [8*mm, 10*mm, 60*mm, 50*mm, 25*mm, 25*mm, 30*mm, 35*mm, 44*mm]
            
            t = Table(data_tabela, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle(tbl_style))
            elements.append(t)
            
            doc.build(elements)
            
            if os.name == 'nt': os.startfile(output_file)
            return True, "PDF Gerado com Sucesso!"
            
        except Exception as e:
            return False, str(e)

# --- INTERFACE GRÁFICA (VIEW) ---
class SistemaUnipGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(TITULO_JANELA)
        self.root.geometry(TAMANHO_JANELA)
        
        # Inicializa Dependências
        self.db = BancoDeDados()
        self.bedel_service = BedelService(self.db)
        self.pdf_service = RelatorioService(self.db)
        
        # Verifica limpeza diária (apenas na janela principal para evitar loops se abrir popups)
        if isinstance(self.root, tk.Tk):
            self.root.after(100, self._verificar_novo_dia)

        self._construir_navegacao()
        self._construir_frames()
        self.mostrar_aba("reserva")

    def _verificar_novo_dia(self):
        hoje = datetime.now().strftime("%d/%m/%Y")
        ultimo_uso = self.db.obter_config('data_ultimo_uso')
        
        if ultimo_uso != hoje:
            self.db.salvar_config('data_ultimo_uso', hoje)
            if ultimo_uso and messagebox.askyesno("Novo Dia", f"Último uso foi em {ultimo_uso}.\nDeseja limpar as reservas anteriores?"):
                self.db.limpar_todas_reservas()
                messagebox.showinfo("Limpeza", "Reservas limpas para o novo dia.")

    def _construir_navegacao(self):
        frm_nav = tk.Frame(self.root, bg=COR_FUNDO, height=50)
        frm_nav.pack(side="top", fill="x")
        
        frm_center = tk.Frame(frm_nav, bg=COR_FUNDO)
        frm_center.pack(pady=10)
        
        style_btn = {"font": ("Arial", 10, "bold"), "relief": "raised", "bd": 2, "width": 18, "pady": 5}
        
        self.btn_nova_janela = tk.Button(frm_center, text="Nova Página", command=self._abrir_nova_janela, **style_btn)
        self.btn_nova_janela.pack(side="left", padx=5)
        
        self.btn_reserva = tk.Button(frm_center, text="Reservas", command=lambda: self.mostrar_aba("reserva"), **style_btn)
        self.btn_reserva.pack(side="left", padx=5)
        
        self.btn_equipe = tk.Button(frm_center, text="Equipe", command=lambda: self.mostrar_aba("equipe"), **style_btn)
        self.btn_equipe.pack(side="left", padx=5)
        
        self.btn_salas = tk.Button(frm_center, text="Gestão de Salas", command=lambda: self.mostrar_aba("salas"), **style_btn)
        self.btn_salas.pack(side="left", padx=5)

    def _abrir_nova_janela(self):
        new_window = tk.Toplevel(self.root)
        app_copy = SistemaUnipGUI(new_window)

    def _construir_frames(self):
        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        self.frames = {
            "reserva": tk.Frame(self.container),
            "equipe": tk.Frame(self.container),
            "salas": tk.Frame(self.container),
            "nova_pagina": tk.Frame(self.container)
        }
        
        for f in self.frames.values():
            f.grid(row=0, column=0, sticky="nsew")
            
        self._setup_aba_reserva()
        self._setup_aba_equipe()
        self._setup_aba_salas()
        self._setup_aba_nova_pagina()

    def mostrar_aba(self, nome):
        # Resetar estilos
        estilo_inativo = {"bg": "#e1e1e1", "fg": "black"}
        self.btn_nova_janela.config(**estilo_inativo)
        self.btn_reserva.config(**estilo_inativo)
        self.btn_equipe.config(**estilo_inativo)
        self.btn_salas.config(**estilo_inativo)
        
        # Ativar
        estilo_ativo = {"bg": COR_PRIMARIA, "fg": "white"}
        if nome == "reserva": self.btn_reserva.config(**estilo_ativo)
        elif nome == "equipe": self.btn_equipe.config(**estilo_ativo)
        elif nome == "salas": self.btn_salas.config(**estilo_ativo)
        elif nome == "nova_pagina": self.btn_nova_janela.config(**estilo_ativo)
        
        self.frames[nome].tkraise()

    # === ABA RESERVA ===
    def _setup_aba_reserva(self):
        frame = self.frames["reserva"]
        frame.columnconfigure(0, weight=1, uniform="gp")
        frame.columnconfigure(1, weight=1, uniform="gp")
        frame.rowconfigure(0, weight=1)
        
        # Painel Esquerdo (Formulário)
        p_esq = tk.LabelFrame(frame, text="Nova Reserva", padx=10, pady=5)
        p_esq.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        p_esq.columnconfigure(0, weight=1)
        
        tk.Label(p_esq, text="Período:", font=("Arial", 10, "bold"), fg="blue").grid(sticky="w")
        
        frm_radio = tk.Frame(p_esq)
        frm_radio.grid(sticky="w", pady=5)
        self.cmb_turno = ttk.Combobox(frm_radio, values=["Diurno", "Noturno"], width=10, state="readonly")
        self.cmb_turno.pack(side="left", padx=(0, 10))
        self.cmb_turno.bind("<<ComboboxSelected>>", self._atualizar_combo_cursos)
        
        self.var_horario = tk.StringVar(value="1")
        tk.Radiobutton(frm_radio, text="1º Horário", variable=self.var_horario, value="1").pack(side="left")
        tk.Radiobutton(frm_radio, text="2º Horário", variable=self.var_horario, value="2").pack(side="left")
        
        self.widgets_reserva = {}
        campos = [
            ("Linha (1-20):", "num", 20),
            ("Professor:", "prof", None),
            ("Curso/Semestre:", "curso", None), # Combobox
            ("Bloco/Sala:", "bloco", None),
            ("Horário:", "hreal", None),        # Combobox
            ("Bedel Data:", "resp", None),
            ("Bedel Auditório:", "audit", None)
        ]
        
        row = 2
        for label, key, width in campos:
            tk.Label(p_esq, text=label).grid(row=row, sticky="w", pady=(5,0))
            row += 1
            
            if key == "curso":
                w = ttk.Combobox(p_esq)
                w.bind("<<ComboboxSelected>>", self._autocompletar_local)
            elif key == "hreal":
                w = ttk.Combobox(p_esq)
            else:
                w = tk.Entry(p_esq)
                if key == "resp":
                    w.insert(0, "Deixe vazio para Auto-Atribuir")
                    w.config(fg="grey")
                    w.bind("<FocusIn>", lambda e, x=w: self._on_placeholder_in(x))
                    w.bind("<FocusOut>", lambda e, x=w: self._on_placeholder_out(x))
            
            w.grid(row=row, sticky="ew")
            self.widgets_reserva[key] = w
            row += 1
            
        tk.Button(p_esq, text="SALVAR RESERVA", bg=COR_PRIMARIA, fg="white", font=("Arial", 11, "bold"), height=2, command=self._salvar_reserva).grid(row=row, sticky="ew", pady=20)

        # Painel Direito (Relatório)
        p_dir = tk.Frame(frame)
        p_dir.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        p_dir.columnconfigure(0, weight=1)
        
        frm_rel = tk.LabelFrame(p_dir, text="Relatório", padx=10, pady=5)
        frm_rel.pack(fill="x")
        
        tk.Label(frm_rel, text="Data:").pack(anchor="w")
        self.ent_data = tk.Entry(frm_rel)
        self.ent_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.ent_data.pack(fill="x", pady=5)
        
        tk.Label(frm_rel, text="Mês:").pack(anchor="w")
        self.ent_mes = tk.Entry(frm_rel)
        self.ent_mes.insert(0, datetime.now().strftime("%B").upper())
        self.ent_mes.pack(fill="x", pady=5)
        
        tk.Label(frm_rel, text="Ano:").pack(anchor="w")
        self.ent_ano = tk.Entry(frm_rel)
        self.ent_ano.insert(0, datetime.now().strftime("%Y"))
        self.ent_ano.pack(fill="x", pady=5)
        
        tk.Button(frm_rel, text="GERAR PDF", bg=COR_SECUNDARIA, fg="white", font=("Arial", 10, "bold"), height=2, command=self._gerar_pdf).pack(fill="x", pady=10)
        
        # Logo
        frm_logo = tk.LabelFrame(p_dir, text="Institucional", padx=10, pady=5)
        frm_logo.pack(fill="both", expand=True, pady=(10, 0))
        
        self.lbl_logo = tk.Label(frm_logo)
        self.lbl_logo.pack(expand=True)
        frm_logo.bind("<Configure>", self._resize_logo)
        
        self._carregar_imagem_logo()

    def _on_placeholder_in(self, entry):
        if entry.get() == "Deixe vazio para Auto-Atribuir":
            entry.delete(0, tk.END)
            entry.config(fg='black')

    def _on_placeholder_out(self, entry):
        if not entry.get():
            entry.insert(0, "Deixe vazio para Auto-Atribuir")
            entry.config(fg='grey')

    def _atualizar_combo_cursos(self, event=None):
        turno = self.cmb_turno.get()
        todos = self.db.listar_salas()
        filtrados = []
        for curso, _ in todos:
            if not turno: filtrados.append(curso)
            elif turno == "Diurno" and "MANHÃ" in curso.upper(): filtrados.append(curso)
            elif turno == "Noturno" and "NOITE" in curso.upper(): filtrados.append(curso)
        
        self.widgets_reserva['curso']['values'] = filtrados
        
        # Horários
        vals = ["08:25 - 11:15"] if turno == "Diurno" else ["17:55 - 20:25", "17:55 - 22:00", "19:10 - 20:25", "19:10 - 22:00", "20:25 - 22:00"]
        self.widgets_reserva['hreal']['values'] = vals

    def _autocompletar_local(self, event):
        local = self.db.buscar_local_sala(self.widgets_reserva['curso'].get())
        if local:
            self.widgets_reserva['bloco'].delete(0, tk.END)
            self.widgets_reserva['bloco'].insert(0, local)

    def _salvar_reserva(self):
        try:
            num = int(self.widgets_reserva['num'].get())
            if not 1 <= num <= 20: raise ValueError
            
            turno = self.cmb_turno.get()
            if not turno: 
                messagebox.showwarning("Aviso", "Selecione o Turno")
                return
            
            # Periodo ID: M1, M2, 1, 2
            periodo_id = f"M{self.var_horario.get()}" if turno == "Diurno" else self.var_horario.get()
            
            # Verificação Conflito (Mensagem Limpa)
            prof_ocupante = self.db.buscar_conflito_reserva(num, periodo_id)
            if prof_ocupante:
                horario_txt = "1º Horário" if "1" in periodo_id else "2º Horário"
                msg = f"Linha {num} já ocupada no {horario_txt} da {turno.upper()} por {prof_ocupante}."
                if not messagebox.askyesno("Conflito", f"{msg}\nSubstituir?"): return

            # Bedel Inteligente
            resp = self.widgets_reserva['resp'].get()
            if resp == "Deixe vazio para Auto-Atribuir": resp = ""
            msg_extra = ""
            
            if not resp.strip():
                bloco = self.widgets_reserva['bloco'].get()
                resp = self.bedel_service.escolher_responsavel_inteligente(bloco)
                msg_extra = f"\n\n🤖 Bedel Auto-Atribuído: {resp}"

            dados = (
                num, periodo_id, 
                self.widgets_reserva['prof'].get(), 
                self.widgets_reserva['curso'].get(), 
                self.widgets_reserva['bloco'].get(), 
                self.widgets_reserva['hreal'].get(), 
                resp, 
                self.widgets_reserva['audit'].get()
            )
            
            if not all(dados[2:6]): # Valida campos obrigatórios
                messagebox.showwarning("Erro", "Preencha Professor, Curso, Bloco e Horário.")
                return

            self.db.salvar_reserva(dados)
            messagebox.showinfo("Sucesso", f"Reserva Salva!{msg_extra}")
            self._limpar_form_reserva()
            
        except ValueError:
            messagebox.showerror("Erro", "Linha deve ser entre 1 e 20")

    def _limpar_form_reserva(self):
        self.widgets_reserva['prof'].delete(0, tk.END)
        self.widgets_reserva['curso'].set('')
        self.widgets_reserva['bloco'].delete(0, tk.END)
        self.widgets_reserva['resp'].delete(0, tk.END)
        self._on_placeholder_out(self.widgets_reserva['resp'])
        self.widgets_reserva['audit'].delete(0, tk.END)
        self.widgets_reserva['num'].focus()

    def _gerar_pdf(self):
        ok, msg = self.pdf_service.gerar_pdf(self.ent_data.get(), self.ent_mes.get(), self.ent_ano.get())
        if ok: messagebox.showinfo("Sucesso", msg)
        else: messagebox.showerror("Erro", msg)

    def _carregar_imagem_logo(self):
        path = Utils.obter_caminho_recurso("logo.png")
        if os.path.exists(path):
            self.img_original = PILImage.open(path)
        else:
            self.img_original = None

    def _resize_logo(self, event):
        if not self.img_original: return
        # Mantem proporção
        razao = min(event.width/self.img_original.width, event.height/self.img_original.height)
        novo_w = int(self.img_original.width * razao)
        novo_h = int(self.img_original.height * razao)
        if novo_w > 0 and novo_h > 0:
            self.tk_image = ImageTk.PhotoImage(self.img_original.resize((novo_w, novo_h), PILImage.LANCZOS))
            self.lbl_logo.config(image=self.tk_image)

    # === ABA EQUIPE ===
    def _setup_aba_equipe(self):
        frame = self.frames["equipe"]
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        
        # Topo
        top = tk.LabelFrame(frame, text="Gerenciar Membros", padx=10, pady=5)
        top.grid(row=0, sticky="ew", padx=10, pady=5)
        top.columnconfigure(5, weight=1) # Input de busca expande
        
        tk.Label(top, text="Nome:").grid(row=0, column=0, padx=5)
        self.ent_eq_nome = tk.Entry(top, width=15)
        self.ent_eq_nome.grid(row=0, column=1, padx=5)
        
        tk.Label(top, text="Especialidade:").grid(row=0, column=2, padx=5)
        self.cmb_eq_esp = ttk.Combobox(top, values=["GERAL", "AUDITÓRIO", "LÍDER"], width=12, state="readonly")
        self.cmb_eq_esp.grid(row=0, column=3, padx=5)
        
        tk.Button(top, text="ADICIONAR", bg=COR_PRIMARIA, fg="white", command=self._add_equipe).grid(row=0, column=4, padx=10)
        
        self.ent_eq_busca = tk.Entry(top)
        self.ent_eq_busca.grid(row=0, column=5, padx=5, sticky="ew")
        
        tk.Button(top, text="Pesquisar", bg=COR_SECUNDARIA, fg="white", command=self._filtrar_equipe).grid(row=0, column=6, padx=5)
        
        # Lista
        cols = ("Nome", "Carga", "Status", "Especialidade")
        self.tree_eq = ttk.Treeview(frame, columns=cols, show="headings", height=12)
        
        # --- LARGURAS FIXAS PARA 700PX ---
        larguras = {"Nome": 180, "Carga": 80, "Status": 120, "Especialidade": 150}
        
        for c in cols:
            self.tree_eq.heading(c, text=c, command=lambda _c=c: self._treeview_sort(self.tree_eq, _c, False))
            self.tree_eq.column(c, width=larguras[c], anchor="center", stretch=True)
            
        self.tree_eq.grid(row=1, sticky="nsew", padx=10, pady=5)
        
        # Ações
        botoes = tk.Frame(frame, pady=10)
        botoes.grid(row=2)
        tk.Button(botoes, text="Alternar Presença", bg=COR_ALERTA, fg="white", command=self._toggle_equipe).pack(side="left", padx=10)
        tk.Button(botoes, text="REMOVER SELECIONADO", bg=COR_PERIGO, fg="white", command=self._del_equipe).pack(side="left", padx=10)
        
        self._filtrar_equipe() # Carrega inicial

    def _treeview_sort(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        try: l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except: l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        
        for index, (_, k) in enumerate(l):
            tv.move(k, '', index)
        
        tv.heading(col, command=lambda: self._treeview_sort(tv, col, not reverse))

    def _filtrar_equipe(self):
        termo = self.ent_eq_busca.get().upper()
        for i in self.tree_eq.get_children(): self.tree_eq.delete(i)
        
        dados = self.db.listar_equipe()
        for nome, carga, disp, esp in dados:
            if termo in nome.upper():
                status = "DISPONÍVEL" if disp == 1 else "AUSENTE"
                self.tree_eq.insert("", "end", values=(nome, carga, status, esp))

    def _add_equipe(self):
        nome = self.ent_eq_nome.get().strip()
        esp = self.cmb_eq_esp.get()
        if not nome or not esp:
            messagebox.showwarning("Aviso", "Preencha nome e especialidade.")
            return
        
        if self.db.adicionar_membro(nome, esp):
            self._filtrar_equipe()
            self.ent_eq_nome.delete(0, tk.END)
            self.cmb_eq_esp.set("")
            messagebox.showinfo("Sucesso", "Membro Adicionado")
        else:
            messagebox.showerror("Erro", "Nome já existe.")

    def _del_equipe(self):
        sel = self.tree_eq.selection()
        if sel:
            nome = self.tree_eq.item(sel[0])['values'][0]
            if messagebox.askyesno("Confirmar", f"Remover {nome}?"):
                self.db.remover_membro(nome)
                self._filtrar_equipe()

    def _toggle_equipe(self):
        sel = self.tree_eq.selection()
        if sel:
            item = self.tree_eq.item(sel[0])['values']
            self.db.alternar_disponibilidade(item[0], item[2])
            self._filtrar_equipe()

    # === ABA SALAS ===
    def _setup_aba_salas(self):
        frame = self.frames["salas"]
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        
        top = tk.LabelFrame(frame, text="Gerenciar Salas", padx=10, pady=5)
        top.grid(row=0, sticky="ew", padx=10, pady=5)
        top.columnconfigure(5, weight=1)
        
        tk.Label(top, text="Curso:").grid(row=0, column=0)
        self.ent_sala_curso = tk.Entry(top, width=20)
        self.ent_sala_curso.grid(row=0, column=1, padx=5)
        
        tk.Label(top, text="Local:").grid(row=0, column=2)
        self.ent_sala_local = tk.Entry(top, width=15)
        self.ent_sala_local.grid(row=0, column=3, padx=5)
        
        tk.Button(top, text="SALVAR", bg=COR_PRIMARIA, fg="white", command=self._salvar_sala).grid(row=0, column=4, padx=10)
        
        self.ent_sala_busca = tk.Entry(top)
        self.ent_sala_busca.grid(row=0, column=5, sticky="ew", padx=5)
        
        tk.Button(top, text="Pesquisar", bg=COR_SECUNDARIA, fg="white", command=self._filtrar_salas).grid(row=0, column=6, padx=5)
        
        self.tree_salas = ttk.Treeview(frame, columns=("Curso", "Local"), show="headings", height=15)
        
        # --- LARGURAS FIXAS PARA SALAS ---
        self.tree_salas.column("Curso", width=300, stretch=True)
        self.tree_salas.column("Local", width=200, stretch=True)
        
        self.tree_salas.heading("Curso", text="Curso / Semestre", command=lambda: self._treeview_sort(self.tree_salas, "Curso", False))
        self.tree_salas.heading("Local", text="Localização Padrão", command=lambda: self._treeview_sort(self.tree_salas, "Local", False))
        
        self.tree_salas.grid(row=1, sticky="nsew", padx=10, pady=5)
        
        self.tree_salas.bind("<<TreeviewSelect>>", self._on_select_sala)
        
        tk.Button(frame, text="REMOVER SELECIONADO", bg=COR_PERIGO, fg="white", command=self._del_sala).grid(row=2, pady=10)
        
        self._filtrar_salas()

    def _filtrar_salas(self):
        termo = self.ent_sala_busca.get().upper()
        for i in self.tree_salas.get_children(): self.tree_salas.delete(i)
        
        dados = self.db.listar_salas()
        for c, l in dados:
            if termo in c.upper() or termo in l.upper():
                self.tree_salas.insert("", "end", values=(c, l))

    def _salvar_sala(self):
        c, l = self.ent_sala_curso.get(), self.ent_sala_local.get()
        if c and l:
            self.db.salvar_sala(c, l)
            self._filtrar_salas()
            self.ent_sala_curso.delete(0, tk.END)
            self.ent_sala_local.delete(0, tk.END)
            messagebox.showinfo("Sucesso", "Sala salva!")

    def _del_sala(self):
        sel = self.tree_salas.selection()
        if sel:
            c = self.tree_salas.item(sel[0])['values'][0]
            if messagebox.askyesno("Confirmar", f"Remover {c}?"):
                self.db.remover_sala(c)
                self._filtrar_salas()

    def _on_select_sala(self, event):
        sel = self.tree_salas.selection()
        if sel:
            item = self.tree_salas.item(sel[0])['values']
            self.ent_sala_curso.delete(0, tk.END)
            self.ent_sala_curso.insert(0, item[0])
            self.ent_sala_local.delete(0, tk.END)
            self.ent_sala_local.insert(0, item[1])

    # === NOVA PÁGINA (PLACEHOLDER) ===
    def _setup_aba_nova_pagina(self):
        frame = self.frames["nova_pagina"]
        tk.Label(frame, text="Nova Página", font=("Arial", 20)).pack(expand=True)
        tk.Label(frame, text="Espaço reservado para futuras implementações", fg="grey").pack()

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    root = tk.Tk()
    app = SistemaUnipGUI(root)
    root.mainloop()