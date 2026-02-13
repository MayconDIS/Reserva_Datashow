"""
SISTEMA DATA SHOW
Versão: 11.27 (Feedback com Estrelas e Placeholder Dinâmico)
Autor: Refatorado por IA (Gemini) / Created by DevMaycon
"""

import sys
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
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
    messagebox.showerror("Erro", f"Instale: pip install Pillow reportlab customtkinter packaging")
    sys.exit()

# --- CONFIGURAÇÃO INICIAL ---
ctk.deactivate_automatic_dpi_awareness()
ctk.set_appearance_mode("System") 
ctk.set_default_color_theme("green") 

# --- CONSTANTES VISUAIS ---
COR_SALVAR = "#4CAF50"    # Verde
COR_PDF = "#2196F3"       # Azul
COR_ALERTA = "#FF9800"    # Laranja
COR_PERIGO = "#F44336"    # Vermelho
COR_NEUTRO = "#444444"    # Cinza para botões inativos
COR_SELECIONADO = "#1f6aa5" # Azul padrão do tema para seleção
COR_PLACEHOLDER = "gray50"  
COR_TEXTO_PADRAO = ("black", "white") 
COR_ESTRELA_ATIVA = "#FFD700" # Amarelo Ouro
COR_ESTRELA_INATIVA = "#555555" # Cinza Escuro

DB_NOME = 'sistema_datashow_v11_ctk.db'

TAMANHO_JANELA = "800x590"  
TITULO_JANELA = "Sistema Data Show (v11.27)"

# Dados Iniciais (Mantidos)
EQUIPE_PADRAO = [
    ("RAFAEL", "GERAL"), ("GABRIEL", "GERAL"), 
    ("DAVID", "GERAL"), ("FERNANDO", "GERAL"), 
    ("MONTEIRO", "GERAL"), ("MAYCON", "GERAL"),
    ("RYAN", "GERAL"), ("JONATHAN", "AUDITÓRIO"), 
    ("LUCAS", "LÍDER"), ("EDUARDO", "LÍDER"),
]

SALAS_PADRAO = [
    ("ADS 2º/3º A", "H - 2º - Sala 02", "MANHÃ"),
    ("CIÊN. COMP 2º/3º A", "H - 2º - Sala 04", "MANHÃ"),
    ("DIREITO 1º A", "F - 1º - Sala 04", "MANHÃ"),
    ("DIREITO 2º/3º A", "F - 1º - Sala 05", "MANHÃ"),
    ("ADS 1º P", "F - 1º - Sala 01", "NOITE"),
    ("ADS 2º P / 3º PQ", "F - 1º - Sala 05", "NOITE"),
    ("ADS 4º PQ", "F - 1º - Sala 02", "NOITE"),
    ("DESIGN GRÁFICO 1º P/4º P", "D - 1º - Sala 06", "NOITE"),
    ("ADM 1º P", "B - 2º - Sala 01", "NOITE"),
    ("DIREITO 1º", "E - 1º - Sala 01", "NOITE")
]

try: locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
except:
    try: locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except: pass

# --- UTILITÁRIOS ---
class Utils:
    @staticmethod
    def obter_caminho_recurso(nome_arquivo):
        try: base_path = sys._MEIPASS
        except Exception:
            try: base_path = os.path.dirname(os.path.abspath(__file__))
            except: base_path = os.path.abspath(".")
        return os.path.join(base_path, nome_arquivo)

    @staticmethod
    def remover_acentos(texto):
        if not texto: return ""
        return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

    @staticmethod
    def extrair_info_bloco(texto_bloco):
        if not texto_bloco: return "", ""
        texto = texto_bloco.upper()
        letra = ""
        match_letra = re.search(r'([A-Z])\s*-', texto)
        if match_letra: letra = match_letra.group(1)
        andar = ""
        if "SUBSOLO" in texto: andar = "SUBSOLO"
        elif "TERREO" in texto: andar = "TERREO"
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

# --- BANCO DE DADOS ---
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
                numero_linha INTEGER, periodo TEXT, professor TEXT, curso TEXT, 
                bloco TEXT, horario_real TEXT, responsavel TEXT, 
                responsavel_auditorio TEXT, contabilizada INTEGER DEFAULT 0, 
                PRIMARY KEY (numero_linha, periodo)
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS equipe (nome TEXT PRIMARY KEY, carga_acumulada INTEGER DEFAULT 0, disponivel INTEGER DEFAULT 1, especialidade TEXT DEFAULT 'GERAL')")
        cursor.execute("CREATE TABLE IF NOT EXISTS salas_turmas (id INTEGER PRIMARY KEY AUTOINCREMENT, curso_semestre TEXT UNIQUE, localizacao TEXT, turno TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nota INTEGER,
                comentario TEXT,
                nome_usuario TEXT,
                email_usuario TEXT,
                data_envio TEXT
            )
        """)
        
        try: cursor.execute("ALTER TABLE reservas ADD COLUMN contabilizada INTEGER DEFAULT 0")
        except: pass
        try: cursor.execute("ALTER TABLE equipe ADD COLUMN especialidade TEXT DEFAULT 'GERAL'")
        except: pass
        try: 
            cursor.execute("ALTER TABLE salas_turmas ADD COLUMN turno TEXT")
            cursor.execute("UPDATE salas_turmas SET turno = 'NOITE' WHERE turno IS NULL") 
        except: pass

        cursor.execute("SELECT count(*) FROM equipe")
        if cursor.fetchone()[0] == 0:
            for nome, esp in EQUIPE_PADRAO:
                try: cursor.execute("INSERT INTO equipe (nome, carga_acumulada, disponivel, especialidade) VALUES (?, 0, 1, ?)", (nome, esp))
                except: pass
        
        cursor.execute("SELECT count(*) FROM salas_turmas")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO salas_turmas (curso_semestre, localizacao, turno) VALUES (?, ?, ?)", SALAS_PADRAO)
            
        conn.commit()
        conn.close()

    def buscar_conflito_reserva(self, linha, periodo):
        with self._conectar() as conn:
            res = conn.execute("SELECT professor FROM reservas WHERE numero_linha = ? AND periodo = ?", (linha, periodo)).fetchone()
        return res[0] if res else None
    
    def listar_linhas_ocupadas(self, periodo):
        with self._conectar() as conn:
            return conn.execute("SELECT numero_linha FROM reservas WHERE periodo = ?", (periodo,)).fetchall()

    def salvar_reserva(self, dados):
        with self._conectar() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO reservas 
                (numero_linha, periodo, professor, curso, bloco, horario_real, responsavel, responsavel_auditorio, contabilizada) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, dados)

    def salvar_feedback(self, nota, comentario, nome, email):
        with self._conectar() as conn:
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT INTO feedbacks (nota, comentario, nome_usuario, email_usuario, data_envio)
                VALUES (?, ?, ?, ?, ?)
            """, (nota, comentario, nome, email, data_atual))

    def listar_todas_reservas(self):
        with self._conectar() as conn:
            return conn.execute("SELECT * FROM reservas ORDER BY numero_linha").fetchall()

    def limpar_todas_reservas(self):
        with self._conectar() as conn:
            conn.execute("DELETE FROM reservas")

    def listar_equipe(self):
        with self._conectar() as conn:
            return conn.execute("SELECT nome, carga_acumulada, disponivel, especialidade FROM equipe ORDER BY nome ASC").fetchall()

    def adicionar_membro(self, nome, especialidade):
        try:
            with self._conectar() as conn:
                conn.execute("INSERT INTO equipe (nome, carga_acumulada, disponivel, especialidade) VALUES (?, 0, 1, ?)", (nome.upper(), especialidade))
            return True
        except: return False

    def remover_membro(self, nome):
        with self._conectar() as conn:
            conn.execute("DELETE FROM equipe WHERE nome = ?", (nome,))

    def alternar_disponibilidade(self, nome, status_atual_str):
        novo_status = 0 if status_atual_str == "DISPONÍVEL" else 1
        with self._conectar() as conn:
            conn.execute("UPDATE equipe SET disponivel = ? WHERE nome = ?", (novo_status, nome))

    def incrementar_carga(self, nome, linha, periodo):
        sucesso = False
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT contabilizada FROM reservas WHERE numero_linha = ? AND periodo = ?", (linha, periodo))
            res = cursor.fetchone()
            if res and res[0] == 0:
                cursor.execute("UPDATE equipe SET carga_acumulada = carga_acumulada + 1 WHERE nome = ?", (nome,))
                cursor.execute("UPDATE reservas SET contabilizada = 1 WHERE numero_linha = ? AND periodo = ?", (linha, periodo))
                conn.commit()
                sucesso = True
        finally:
            conn.close()
        return sucesso

    def listar_salas(self):
        with self._conectar() as conn:
            return conn.execute("SELECT curso_semestre, localizacao, turno FROM salas_turmas ORDER BY curso_semestre ASC").fetchall()

    def salvar_sala(self, curso, local, turno):
        with self._conectar() as conn:
            conn.execute("INSERT OR REPLACE INTO salas_turmas (curso_semestre, localizacao, turno) VALUES (?, ?, ?)", (curso, local, turno))

    def remover_sala(self, curso):
        with self._conectar() as conn:
            conn.execute("DELETE FROM salas_turmas WHERE curso_semestre = ?", (curso,))

    def buscar_local_sala(self, curso):
        with self._conectar() as conn:
            res = conn.execute("SELECT localizacao FROM salas_turmas WHERE curso_semestre = ?", (curso,)).fetchone()
        return res[0] if res else None

    def obter_config(self, chave):
        with self._conectar() as conn:
            res = conn.execute("SELECT valor FROM config WHERE chave = ?", (chave,)).fetchone()
        return res[0] if res else None

    def salvar_config(self, chave, valor):
        with self._conectar() as conn:
            conn.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)", (chave, valor))

# --- LÓGICA DE NEGÓCIO ---
class BedelService:
    def __init__(self, db: BancoDeDados):
        self.db = db

    def escolher_responsavel_inteligente(self, bloco_alvo):
        equipe = self.db.listar_equipe()
        equipe_disponivel = [m for m in equipe if m[2] == 1]
        if not equipe_disponivel: return "SEM EQUIPE"

        reservas_hoje = self.db.listar_todas_reservas()
        locais_responsavel = {m[0]: [] for m in equipe_disponivel}
        carga_atual = {m[0]: m[1] for m in equipe_disponivel}

        for r in reservas_hoje:
            resp = r[6]
            bloco = r[4]
            if resp in locais_responsavel:
                locais_responsavel[resp].append(bloco)
                carga_atual[resp] += 1 

        candidatos = []
        especialistas_auditorio = []
        bloco_norm = Utils.remover_acentos(bloco_alvo)
        eh_auditorio = "AUDITORIO" in bloco_norm

        for nome, _, _, esp in equipe_disponivel:
            if esp == "AUDITÓRIO": especialistas_auditorio.append(nome)
            penalidade_dist = Utils.calcular_penalidade_distancia(bloco_alvo, locais_responsavel[nome])
            score = (carga_atual[nome] * 3) + penalidade_dist
            candidatos.append((nome, score))

        if eh_auditorio and especialistas_auditorio:
            melhor = sorted(especialistas_auditorio, key=lambda n: carga_atual[n])[0]
            return melhor

        candidatos.sort(key=lambda x: x[1])
        return candidatos[0][0]

class RelatorioService:
    def __init__(self, db: BancoDeDados):
        self.db = db

    def gerar_pdf(self, data_cabecalho, mes_referencia, ano_referencia):
        try:
            try: mes_safe = mes_referencia.upper().split()[0]
            except: mes_safe = "MES"
            output_file = Utils.obter_caminho_recurso(f"Reserva_{mes_safe}_{ano_referencia}.pdf")
            caminho_logo = Utils.obter_caminho_recurso("logo.png")
            
            doc = SimpleDocTemplate(output_file, pagesize=landscape(A4), 
                                    rightMargin=5*mm, leftMargin=5*mm, topMargin=5*mm, bottomMargin=5*mm)
            elements = []
            
            if os.path.exists(caminho_logo):
                im = Image(caminho_logo, width=1.5*inch, height=0.4*inch)
                im.hAlign = 'CENTER' 
                elements.append(im)
                elements.append(Spacer(1, 1*mm))
            
            styles = getSampleStyleSheet()
            estilo_titulo = ParagraphStyle('TituloCenter', parent=styles['Normal'], fontSize=12, alignment=1)
            
            reservas = self.db.listar_todas_reservas()
            texto_auditorio = "_______________"
            for r in reservas:
                if len(r) > 7 and r[7] and r[7].strip():
                    texto_auditorio = r[7].strip().upper()
                    break
            
            titulo = f"<b>RESERVA DE DATA SHOW | DIA: {data_cabecalho} - {mes_referencia.upper()}/{ano_referencia} | AUDITÓRIO: {texto_auditorio}</b>"
            elements.append(Paragraph(titulo, estilo_titulo))
            elements.append(Spacer(1, 3*mm))
            
            linhas_dict = {i: [] for i in range(1, 21)}
            for r in reservas: linhas_dict[r[0]].append(r)
            
            lista_ordenada = []
            for num in range(1, 21):
                itens = linhas_dict[num]
                bloco_chave = itens[0][4] if itens and itens[0][4] else "ZZZ"
                lista_ordenada.append((num, bloco_chave, itens))
            
            lista_ordenada.sort(key=lambda x: (x[1], x[0]))
            
            headers = ['Nº', 'HORA', 'PROFESSOR', 'CURSO', 'BLOCO', 'HORÁRIO', 'SOM/MIC', 'RESPONSÁVEL', 'Montou x Desmontou']
            data_tabela = [headers]
            
            tbl_style = [
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TOPPADDING', (0,0), (-1,-1), 1.6), ('BOTTOMPADDING', (0,0), (-1,-1), 1.6),
                ('LEFTPADDING', (0,0), (-1,-1), 1), ('RIGHTPADDING', (0,0), (-1,-1), 1),
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

                tem_manha = any(i[1] in ['M1', 'M2'] for i in itens_linha)
                p1 = 'M1' if tem_manha else '1'
                p2 = 'M2' if tem_manha else '2'
                
                linha1 = [str(num_linha), "1º"] + extrair(p1)
                linha2 = ["", "2º"] + extrair(p2)
                
                data_tabela.append(linha1)
                data_tabela.append(linha2)
                tbl_style.append(('SPAN', (0, row_idx), (0, row_idx+1)))
                row_idx += 2
            
            col_widths = [8*mm, 10*mm, 60*mm, 50*mm, 25*mm, 25*mm, 30*mm, 35*mm, 44*mm]
            t = Table(data_tabela, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle(tbl_style))
            elements.append(t)
            doc.build(elements)
            
            if os.name == 'nt': os.startfile(output_file)
            return True, "PDF Gerado com Sucesso!"
        except Exception as e:
            return False, str(e)

# --- INTERFACE GRÁFICA ---
class SistemaUnipApp(ctk.CTk):
    def __init__(self, is_child=False):
        super().__init__()
        self.is_child = is_child
        
        self.title(TITULO_JANELA)
        self.geometry(TAMANHO_JANELA)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0) 
        self.grid_columnconfigure(0, weight=1)

        self.db = BancoDeDados()
        self.bedel_service = BedelService(self.db)
        self.pdf_service = RelatorioService(self.db)

        self.linha_selecionada = 1 
        self.botoes_linhas = {} 

        if not self.is_child:
            self.protocol("WM_DELETE_WINDOW", self._on_close_app)
            self.after(200, self._verificar_novo_dia)
        else:
            self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._criar_tabs()
        self._criar_rodape() 

    def _on_close_app(self):
        self.destroy()
        sys.exit()

    def _verificar_novo_dia(self):
        hoje = datetime.now().strftime("%d/%m/%Y")
        ultimo_uso = self.db.obter_config('data_ultimo_uso')
        if ultimo_uso != hoje:
            self.db.salvar_config('data_ultimo_uso', hoje)
            if ultimo_uso and messagebox.askyesno("Novo Dia", f"Último uso: {ultimo_uso}.\nLimpar reservas anteriores?"):
                self.db.limpar_todas_reservas()
                messagebox.showinfo("Limpeza", "Reservas limpas.")
                self._limpar_form_reserva()
                self._atualizar_botoes_ocupados()

    def _criar_tabs(self):
        self.tabview = ctk.CTkTabview(self, width=780)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.tabview._segmented_button.configure(font=ctk.CTkFont(size=15, weight="bold"), height=35)
        
        self.tab_reserva = self.tabview.add("Reservas")
        self.tab_salas = self.tabview.add("Salas") 
        self.tab_equipe = self.tabview.add("Equipe")
        
        self.tab_reserva.grid_columnconfigure(0, weight=3)
        self.tab_reserva.grid_columnconfigure(1, weight=1)
        self.tab_reserva.grid_rowconfigure(0, weight=1)
        
        self.tab_equipe.grid_columnconfigure(0, weight=1)
        self.tab_equipe.grid_rowconfigure(1, weight=1)

        self.tab_salas.grid_columnconfigure(0, weight=1)
        self.tab_salas.grid_rowconfigure(1, weight=1)

        self._setup_aba_reserva()
        self._setup_aba_salas() 
        self._setup_aba_equipe()

    # --- NOVO SISTEMA DE FEEDBACK ATUALIZADO ---
    def _clique_feedback(self):
        self.janela_feedback = ctk.CTkToplevel(self)
        self.janela_feedback.title("Enviar Feedback")
        self.janela_feedback.geometry("400x500") 
        self.janela_feedback.resizable(False, False)
        
        self.janela_feedback.transient(self)
        self.janela_feedback.grab_set()
        
        ctk.CTkLabel(self.janela_feedback, text="Seu feedback é importante!", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        
        # (1) Texto atualizado
        ctk.CTkLabel(self.janela_feedback, text="Sua avaliação:").pack(pady=(10, 5))
        
        # (2) Sistema de Estrelas
        frm_stars = ctk.CTkFrame(self.janela_feedback, fg_color="transparent")
        frm_stars.pack(pady=5)
        
        self.botoes_estrelas = []
        self.nota_atual = 5 # Começa com 5 estrelas
        
        for i in range(1, 6):
            btn = ctk.CTkButton(
                frm_stars, 
                text="★", 
                width=40, 
                height=40,
                fg_color="transparent", 
                hover_color="#333",
                font=ctk.CTkFont(size=30),
                text_color=COR_ESTRELA_ATIVA, # Começa amarelo
                command=lambda nota=i: self._atualizar_estrelas(nota)
            )
            btn.pack(side="left", padx=2)
            self.botoes_estrelas.append(btn)
        
        # (3) Texto de Placeholder dentro da caixa
        self.txt_feedback = ctk.CTkTextbox(self.janela_feedback, height=120, width=320, text_color="gray")
        self.txt_feedback.pack(pady=(15, 5))
        
        # Inserir placeholder
        self.txt_feedback.insert("1.0", "Comentários, sugestões ou bugs...")
        
        # Bindings para limpar/restaurar placeholder
        self.txt_feedback.bind("<FocusIn>", self._foco_entrada_texto)
        self.txt_feedback.bind("<FocusOut>", self._foco_saida_texto)
        self.feedback_placeholder_ativo = True
        
        ctk.CTkLabel(self.janela_feedback, text="Suas informações (Opcional):", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(15, 5))
        
        self.ent_fb_nome = ctk.CTkEntry(self.janela_feedback, placeholder_text="Seu Nome", width=320)
        self.ent_fb_nome.pack(pady=5)
        
        self.ent_fb_email = ctk.CTkEntry(self.janela_feedback, placeholder_text="Seu melhor Email", width=320)
        self.ent_fb_email.pack(pady=5)
        
        ctk.CTkButton(self.janela_feedback, text="ENVIAR FEEDBACK", fg_color=COR_SALVAR, width=200, command=self._enviar_feedback).pack(pady=30)

    def _atualizar_estrelas(self, nota):
        self.nota_atual = nota
        for i, btn in enumerate(self.botoes_estrelas):
            # Se o índice da estrela (0 a 4) for menor que a nota selecionada (1 a 5)
            if i < nota:
                btn.configure(text_color=COR_ESTRELA_ATIVA)
            else:
                btn.configure(text_color=COR_ESTRELA_INATIVA)

    def _foco_entrada_texto(self, event):
        if self.feedback_placeholder_ativo:
            self.txt_feedback.delete("1.0", "end")
            self.txt_feedback.configure(text_color=COR_TEXTO_PADRAO)
            self.feedback_placeholder_ativo = False

    def _foco_saida_texto(self, event):
        texto = self.txt_feedback.get("1.0", "end-1c").strip()
        if not texto:
            self.txt_feedback.configure(text_color="gray")
            self.txt_feedback.insert("1.0", "Comentários, sugestões ou bugs...")
            self.feedback_placeholder_ativo = True

    def _enviar_feedback(self):
        # Se o placeholder estiver ativo, o texto real é vazio
        texto = "" if self.feedback_placeholder_ativo else self.txt_feedback.get("1.0", "end-1c").strip()
        
        if not texto:
            messagebox.showwarning("Aviso", "Por favor, escreva algum comentário.")
            return
            
        nome = self.ent_fb_nome.get().strip()
        email = self.ent_fb_email.get().strip()
        
        try:
            self.db.salvar_feedback(self.nota_atual, texto, nome, email)
            messagebox.showinfo("Sucesso", "Feedback enviado com sucesso!\nObrigado por contribuir.")
            self.janela_feedback.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar feedback: {e}")

    def _criar_rodape(self):
        lbl_rodape = ctk.CTkLabel(
            self, 
            text="Created by DevMaycon", 
            font=ctk.CTkFont(size=11),
            text_color="gray50"
        )
        lbl_rodape.grid(row=1, column=0, sticky="ew", pady=(0, 5)) 

    # --- NOVO MÉTODO PARA ORDENAÇÃO DE TREEVIEW ---
    def _treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        
        try:
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            l.sort(key=lambda t: t[0].lower(), reverse=reverse)

        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        tv.heading(col, command=lambda: self._treeview_sort_column(tv, col, not reverse))

    # === ABA RESERVA ===
    def _setup_aba_reserva(self):
        self.frm_esq = ctk.CTkFrame(self.tab_reserva, border_width=1, border_color="#555555")
        self.frm_esq.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        self.frm_esq.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frm_esq, text="NOVA RESERVA", font=ctk.CTkFont(size=14, weight="bold"), text_color="#AAAAAA").pack(pady=10)

        # 1. Linha do Turno e Horário
        frm_turno_row = ctk.CTkFrame(self.frm_esq, fg_color="transparent")
        frm_turno_row.pack(fill="x", padx=15, pady=5)
        
        self.cmb_turno = ctk.CTkComboBox(frm_turno_row, values=["Diurno", "Noturno"], width=120, command=self._ao_mudar_turno_ou_horario)
        self.cmb_turno.pack(side="left", padx=(0, 10))
        self.cmb_turno.set("Turno") 
        self.cmb_turno.configure(text_color=COR_PLACEHOLDER)

        self.var_horario = tk.StringVar(value="1")
        r1 = ctk.CTkRadioButton(frm_turno_row, text="1º Horário", variable=self.var_horario, value="1", command=self._atualizar_botoes_ocupados)
        r1.pack(side="left", padx=5)
        r2 = ctk.CTkRadioButton(frm_turno_row, text="2º Horário", variable=self.var_horario, value="2", command=self._atualizar_botoes_ocupados)
        r2.pack(side="left", padx=5)

        # 2. Grid de Botões
        frm_botoes = ctk.CTkFrame(self.frm_esq, fg_color="transparent")
        frm_botoes.pack(fill="x", padx=15, pady=5)
        
        for i in range(10):
            frm_botoes.grid_columnconfigure(i, weight=1)

        for i in range(1, 21):
            btn = ctk.CTkButton(
                frm_botoes, 
                text=str(i), 
                width=30,   
                height=24, 
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=COR_NEUTRO,
                command=lambda linha=i: self._selecionar_linha_botao(linha)
            )
            row_btn = 0 if i <= 10 else 1
            col_btn = (i - 1) if i <= 10 else (i - 11)
            btn.grid(row=row_btn, column=col_btn, padx=2, pady=2, sticky="ew")
            self.botoes_linhas[i] = btn

        self._selecionar_linha_botao(1)

        # 3. Campos de Entrada
        self.widgets_reserva = {}

        self.ent_prof = ctk.CTkEntry(self.frm_esq, placeholder_text="Professor", height=30)
        self.ent_prof.pack(fill="x", padx=15, pady=5)
        self.widgets_reserva['prof'] = self.ent_prof

        self.cmb_curso = ctk.CTkComboBox(self.frm_esq, values=[], height=30, command=self._wrapper_curso)
        self.cmb_curso.set("Curso/Semestre")
        self.cmb_curso.configure(text_color=COR_PLACEHOLDER)
        self.cmb_curso.pack(fill="x", padx=15, pady=5)
        self.widgets_reserva['curso'] = self.cmb_curso

        self.ent_bloco = ctk.CTkEntry(self.frm_esq, placeholder_text="Bloco/Sala", height=30)
        self.ent_bloco.pack(fill="x", padx=15, pady=5)
        self.widgets_reserva['bloco'] = self.ent_bloco

        self.cmb_hreal = ctk.CTkComboBox(self.frm_esq, values=[], height=30, command=self._ao_mudar_hreal_reserva)
        self.cmb_hreal.set("Horário")
        self.cmb_hreal.configure(text_color=COR_PLACEHOLDER)
        self.cmb_hreal.pack(fill="x", padx=15, pady=5)
        self.widgets_reserva['hreal'] = self.cmb_hreal

        self.ent_bedel = ctk.CTkEntry(self.frm_esq, placeholder_text="Bedel", height=30)
        self.ent_bedel.pack(fill="x", padx=15, pady=5)
        self.widgets_reserva['resp'] = self.ent_bedel

        self.ent_audit = ctk.CTkEntry(self.frm_esq, placeholder_text="Resp. Auditório", height=30)
        self.ent_audit.pack(fill="x", padx=15, pady=5)
        self.widgets_reserva['audit'] = self.ent_audit

        self.btn_salvar = ctk.CTkButton(self.frm_esq, text="SALVAR RESERVA", width=200, fg_color=COR_SALVAR, height=35, font=ctk.CTkFont(size=13, weight="bold"), command=self._salvar_reserva)
        self.btn_salvar.pack(pady=20)


        # --- COLUNA DIREITA ---
        self.frm_dir = ctk.CTkFrame(self.tab_reserva, border_width=1, border_color="#555555")
        self.frm_dir.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
        self.frm_dir.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.frm_dir, text="RELATÓRIO PDF", font=ctk.CTkFont(size=13, weight="bold"), text_color="#AAAAAA").pack(pady=(15, 10))

        self.ent_data = ctk.CTkEntry(self.frm_dir, placeholder_text="Dia", height=28)
        self.ent_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.ent_data.pack(fill="x", padx=15, pady=5)
        
        self.ent_mes = ctk.CTkEntry(self.frm_dir, placeholder_text="Mês", height=28)
        self.ent_mes.insert(0, datetime.now().strftime("%B").upper())
        self.ent_mes.pack(fill="x", padx=15, pady=5)
        
        self.ent_ano = ctk.CTkEntry(self.frm_dir, placeholder_text="Ano", height=28)
        self.ent_ano.insert(0, datetime.now().strftime("%Y"))
        self.ent_ano.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkButton(self.frm_dir, text="GERAR PDF", fg_color=COR_PDF, height=35, font=ctk.CTkFont(size=12), command=self._gerar_pdf).pack(fill="x", padx=15, pady=20)
        
        # Botão Feedback
        self.btn_feedback = ctk.CTkButton(self.frm_dir, text="Feedback", width=100, height=25, fg_color="#555", hover_color="#666", command=self._clique_feedback)
        self.btn_feedback.pack(side="bottom", pady=(5, 20)) 

        # Logo
        self.lbl_logo = ctk.CTkLabel(self.frm_dir, text="")
        self.lbl_logo.pack(side="bottom", pady=(20, 5)) 
        
        self._carregar_imagem_logo()
        self._atualizar_combo_cursos(None)

    # --- Wrappers para cores de Placeholder ---
    def _ao_mudar_turno_reserva(self, choice):
        if choice == "Turno":
            self.cmb_turno.configure(text_color=COR_PLACEHOLDER)
        else:
            self.cmb_turno.configure(text_color=COR_TEXTO_PADRAO)
        self._ao_mudar_turno_ou_horario(None)

    def _wrapper_curso(self, choice):
        if choice == "Curso/Semestre":
            self.cmb_curso.configure(text_color=COR_PLACEHOLDER)
        else:
            self.cmb_curso.configure(text_color=COR_TEXTO_PADRAO)
        self._autocompletar_local(choice)

    def _ao_mudar_hreal_reserva(self, choice):
        if choice == "Horário":
            self.cmb_hreal.configure(text_color=COR_PLACEHOLDER)
        else:
            self.cmb_hreal.configure(text_color=COR_TEXTO_PADRAO)

    def _ao_mudar_turno_ou_horario(self, event=None):
        self._atualizar_combo_cursos(event)
        self._atualizar_botoes_ocupados()

    def _carregar_imagem_logo(self):
        path = Utils.obter_caminho_recurso("logo.png")
        if os.path.exists(path):
            try:
                pil_img = PILImage.open(path)
                razao = 145 / pil_img.width 
                h = int(pil_img.height * razao)
                self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(145, h))
                self.lbl_logo.configure(image=self.logo_image)
            except: self.lbl_logo.configure(text="[Logo]")
        else:
            self.lbl_logo.configure(text="[Sem Logo]")

    def _atualizar_combo_cursos(self, event):
        turno = self.cmb_turno.get()
        todos = self.db.listar_salas()
        filtrados = []
        for curso, _, turno_curso in todos:
            turno_curso_up = turno_curso.upper() if turno_curso else ""
            if turno == "Diurno":
                if any(x in turno_curso_up for x in ["MANHÃ", "MANHA", "DIURNO"]): filtrados.append(curso)
            else:
                if any(x in turno_curso_up for x in ["NOITE", "NOTURNO"]): filtrados.append(curso)
            if not turno_curso: filtrados.append(curso)

        vals_h = ["08:25 - 11:15"] if turno == "Diurno" else ["17:55 - 20:25", "17:55 - 22:00", "19:10 - 20:25", "19:10 - 22:00", "20:25 - 22:00"]
        
        self.widgets_reserva['curso'].configure(values=sorted(list(set(filtrados))))
        self.widgets_reserva['hreal'].configure(values=vals_h)
        self.widgets_reserva['curso'].set("Curso/Semestre")
        self.widgets_reserva['hreal'].set("Horário")
        self.widgets_reserva['curso'].configure(text_color=COR_PLACEHOLDER)
        self.widgets_reserva['hreal'].configure(text_color=COR_PLACEHOLDER)

    def _autocompletar_local(self, choice):
        local = self.db.buscar_local_sala(choice)
        if local:
            self.widgets_reserva['bloco'].delete(0, tk.END)
            self.widgets_reserva['bloco'].insert(0, local)

    def _selecionar_linha_botao(self, numero_linha):
        self.linha_selecionada = numero_linha
        self._atualizar_botoes_ocupados()

    def _atualizar_botoes_ocupados(self):
        turno = self.cmb_turno.get()
        if not turno or turno == "Turno": return 
        
        periodo_id = f"M{self.var_horario.get()}" if turno == "Diurno" else self.var_horario.get()
        
        linhas_ocupadas_raw = self.db.listar_linhas_ocupadas(periodo_id)
        linhas_ocupadas = [r[0] for r in linhas_ocupadas_raw]

        for i in range(1, 21):
            btn = self.botoes_linhas[i]
            if i == self.linha_selecionada:
                btn.configure(fg_color=COR_SELECIONADO, text=str(i))
            elif i in linhas_ocupadas:
                btn.configure(fg_color=COR_SALVAR, text="✓") 
            else:
                btn.configure(fg_color=COR_NEUTRO, text=str(i))

    def _salvar_reserva(self):
        try:
            num = self.linha_selecionada
            turno = self.cmb_turno.get()
            if not turno or turno == "Turno":
                messagebox.showwarning("Aviso", "Selecione um Turno.")
                return

            periodo_id = f"M{self.var_horario.get()}" if turno == "Diurno" else self.var_horario.get()
            
            prof_ocupante = self.db.buscar_conflito_reserva(num, periodo_id)
            if prof_ocupante:
                 if not messagebox.askyesno("Conflito", f"Linha {num} ocupada por {prof_ocupante}. Substituir?"): return

            resp = self.widgets_reserva['resp'].get()
            if not resp.strip():
                bloco = self.widgets_reserva['bloco'].get()
                resp = self.bedel_service.escolher_responsavel_inteligente(bloco)

            # Validação dos campos
            prof = self.widgets_reserva['prof'].get()
            curso = self.widgets_reserva['curso'].get()
            if curso == "Curso/Semestre": curso = ""
            
            bloco = self.widgets_reserva['bloco'].get()
            
            hreal = self.widgets_reserva['hreal'].get()
            if hreal == "Horário": hreal = ""

            dados = (
                num, periodo_id, prof, curso, bloco, hreal, resp, self.widgets_reserva['audit'].get()
            )
            
            if not all([prof, curso, bloco, hreal]): 
                messagebox.showwarning("Erro", "Preencha Professor, Curso, Bloco e Horário.")
                return

            self.db.salvar_reserva(dados)

            # --- LÓGICA DE 1º E 2º HORÁRIO ---
            periodo_atual = self.var_horario.get()
            
            if periodo_atual == "1":
                if messagebox.askyesno("Extender Reserva", "Deseja reservar também para o 2º Horário?"):
                    self.var_horario.set("2")
                    self._atualizar_botoes_ocupados()
                    return

            self._limpar_form_reserva()
            self._atualizar_botoes_ocupados()
            
            if self.linha_selecionada < 20:
                self._selecionar_linha_botao(self.linha_selecionada + 1)
                self.var_horario.set("1") 
                
        except ValueError: messagebox.showerror("Erro", "Erro ao processar linha.")

    def _limpar_form_reserva(self):
        self.widgets_reserva['prof'].delete(0, tk.END)
        
        self.widgets_reserva['curso'].set("Curso/Semestre")
        self.widgets_reserva['curso'].configure(text_color=COR_PLACEHOLDER)
        
        self.widgets_reserva['hreal'].set("Horário")
        self.widgets_reserva['hreal'].configure(text_color=COR_PLACEHOLDER)
        
        self.widgets_reserva['bloco'].delete(0, tk.END)
        self.widgets_reserva['resp'].delete(0, tk.END)
        self.widgets_reserva['audit'].delete(0, tk.END)

    def _gerar_pdf(self):
        ok, msg = self.pdf_service.gerar_pdf(self.ent_data.get(), self.ent_mes.get(), self.ent_ano.get())
        if ok: messagebox.showinfo("PDF", msg)
        else: messagebox.showerror("Erro PDF", msg)

    # === ABA EQUIPE ===
    def _setup_aba_equipe(self):
        top = ctk.CTkFrame(self.tab_equipe)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.ent_eq_nome = ctk.CTkEntry(top, placeholder_text="Nome", width=150)
        self.ent_eq_nome.pack(side="left", padx=5)
        
        self.cmb_eq_esp = ctk.CTkComboBox(top, values=["GERAL", "AUDITÓRIO", "LÍDER"], width=120, command=self._ao_mudar_especialidade)
        self.cmb_eq_esp.pack(side="left", padx=5)
        self.cmb_eq_esp.set("Especialidade") 
        self.cmb_eq_esp.configure(text_color=COR_PLACEHOLDER)
        
        ctk.CTkButton(top, text="🔍", width=40, fg_color=COR_PDF, command=self._filtrar_equipe).pack(side="right")
        self.ent_eq_busca = ctk.CTkEntry(top, placeholder_text="Pesquisar...")
        self.ent_eq_busca.pack(side="right", padx=5)

        self._configurar_estilo_treeview()
        
        cols = ("Nome", "Carga", "Status", "Especialidade")
        self.tree_eq = ttk.Treeview(self.tab_equipe, columns=cols, show="headings", height=15)
        for c in cols:
            self.tree_eq.heading(c, text=c, command=lambda _c=c: self._treeview_sort_column(self.tree_eq, _c, False))
            self.tree_eq.column(c, anchor="center")
        self.tree_eq.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        bot = ctk.CTkFrame(self.tab_equipe, fg_color="transparent")
        bot.grid(row=2, column=0, pady=10)
        
        ctk.CTkButton(bot, text="SALVAR", width=100, fg_color=COR_SALVAR, command=self._add_equipe).pack(side="left", padx=10)
        ctk.CTkButton(bot, text="Alternar Presença", fg_color=COR_ALERTA, command=self._toggle_equipe).pack(side="left", padx=10)
        ctk.CTkButton(bot, text="Remover Selecionado", fg_color=COR_PERIGO, command=self._del_equipe).pack(side="left", padx=10)
        
        self._filtrar_equipe()

    # Gerencia cor do Placeholder na aba Equipe
    def _ao_mudar_especialidade(self, choice):
        if choice == "Especialidade":
            self.cmb_eq_esp.configure(text_color=COR_PLACEHOLDER)
        else:
            self.cmb_eq_esp.configure(text_color=COR_TEXTO_PADRAO)

    def _configurar_estilo_treeview(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", bordercolor="#2b2b2b", rowheight=25)
        style.configure("Treeview.Heading", background="#3a3a3a", foreground="white", relief="flat")
        style.map("Treeview", background=[('selected', '#1f538d')])

    def _filtrar_equipe(self):
        for i in self.tree_eq.get_children(): self.tree_eq.delete(i)
        termo = self.ent_eq_busca.get().upper()
        for nome, carga, disp, esp in self.db.listar_equipe():
            if termo in nome.upper():
                self.tree_eq.insert("", "end", values=(nome, carga, "DISPONÍVEL" if disp == 1 else "AUSENTE", esp))

    def _add_equipe(self):
        nome = self.ent_eq_nome.get().strip()
        esp = self.cmb_eq_esp.get()
        if esp == "Especialidade": esp = ""

        if nome and esp and self.db.adicionar_membro(nome, esp):
            self._filtrar_equipe()
            self.ent_eq_nome.delete(0, tk.END)
            self.cmb_eq_esp.set("Especialidade")
            self.cmb_eq_esp.configure(text_color=COR_PLACEHOLDER)
        else: messagebox.showwarning("Erro", "Inválido.")

    def _toggle_equipe(self):
        sel = self.tree_eq.selection()
        if sel:
            item = self.tree_eq.item(sel[0])['values']
            self.db.alternar_disponibilidade(item[0], item[2])
            self._filtrar_equipe()

    def _del_equipe(self):
        sel = self.tree_eq.selection()
        if sel:
            if messagebox.askyesno("Confirmar", "Remover?"):
                self.db.remover_membro(self.tree_eq.item(sel[0])['values'][0])
                self._filtrar_equipe()

    # === ABA SALAS (ANTIGA GESTÃO DE SALAS) ===
    def _setup_aba_salas(self):
        top = ctk.CTkFrame(self.tab_salas)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.ent_sala_curso = ctk.CTkEntry(top, placeholder_text="Curso", width=130)
        self.ent_sala_curso.pack(side="left", padx=5)
        
        vals_semestre = [f"{i}º" for i in range(1, 11)]
        self.cmb_sala_semestre = ctk.CTkComboBox(top, values=vals_semestre, width=100, command=self._ao_mudar_semestre)
        self.cmb_sala_semestre.pack(side="left", padx=5)
        self.cmb_sala_semestre.set("Semestre")
        self.cmb_sala_semestre.configure(text_color=COR_PLACEHOLDER)

        self.cmb_sala_turno = ctk.CTkComboBox(top, values=["MANHÃ", "NOITE"], width=100, command=self._ao_mudar_turno_salas)
        self.cmb_sala_turno.pack(side="left", padx=5)
        self.cmb_sala_turno.set("Turno") 
        self.cmb_sala_turno.configure(text_color=COR_PLACEHOLDER)
        
        self.ent_sala_local = ctk.CTkEntry(top, placeholder_text="Local", width=150)
        self.ent_sala_local.pack(side="left", padx=5)
        
        ctk.CTkButton(top, text="🔍", width=40, fg_color=COR_PDF, command=self._filtrar_salas).pack(side="right", padx=5)
        self.ent_sala_busca = ctk.CTkEntry(top, placeholder_text="Filtrar...")
        self.ent_sala_busca.pack(side="right", padx=5)

        self.tree_salas = ttk.Treeview(self.tab_salas, columns=("Curso", "Turno", "Local"), show="headings")
        cols_sala = ("Curso", "Turno", "Local")
        
        self.tree_salas.heading("Curso", text="Curso / Semestre", command=lambda: self._treeview_sort_column(self.tree_salas, "Curso", False))
        self.tree_salas.heading("Turno", text="Turno", command=lambda: self._treeview_sort_column(self.tree_salas, "Turno", False))
        self.tree_salas.heading("Local", text="Localização", command=lambda: self._treeview_sort_column(self.tree_salas, "Local", False))
        
        self.tree_salas.column("Curso", width=300)
        self.tree_salas.column("Turno", width=100, anchor="center")
        self.tree_salas.column("Local", width=200)
        self.tree_salas.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.tree_salas.bind("<<TreeviewSelect>>", self._on_select_sala)
        
        bot = ctk.CTkFrame(self.tab_salas, fg_color="transparent")
        bot.grid(row=2, column=0, pady=10)
        
        ctk.CTkButton(bot, text="SALVAR", fg_color=COR_SALVAR, command=self._salvar_sala).pack(side="left", padx=10)
        ctk.CTkButton(bot, text="Remover Sala", fg_color=COR_PERIGO, command=self._del_sala).pack(side="left", padx=10)
        
        self._filtrar_salas()

    def _ao_mudar_turno_salas(self, choice):
        if choice == "Turno":
            self.cmb_sala_turno.configure(text_color=COR_PLACEHOLDER)
        else:
            self.cmb_sala_turno.configure(text_color=COR_TEXTO_PADRAO)

    def _ao_mudar_semestre(self, choice):
        if choice == "Semestre":
            self.cmb_sala_semestre.configure(text_color=COR_PLACEHOLDER)
        else:
            self.cmb_sala_semestre.configure(text_color=COR_TEXTO_PADRAO)

    def _filtrar_salas(self):
        termo = self.ent_sala_busca.get().upper()
        for i in self.tree_salas.get_children(): self.tree_salas.delete(i)
        for c, l, t in self.db.listar_salas():
            if termo in c.upper() or termo in l.upper():
                self.tree_salas.insert("", "end", values=(c, t if t else "-", l))

    def _salvar_sala(self):
        c = self.ent_sala_curso.get()
        s = self.cmb_sala_semestre.get()
        t = self.cmb_sala_turno.get()
        l = self.ent_sala_local.get()

        if t == "Turno": t = "" 
        if s == "Semestre": s = ""

        nome_final = c
        if s:
            nome_final = f"{c} {s}"

        if nome_final and l:
            self.db.salvar_sala(nome_final, l, t)
            self._filtrar_salas()
            self.ent_sala_curso.delete(0, tk.END)
            self.ent_sala_local.delete(0, tk.END)
            self.cmb_sala_turno.set("Turno")
            self.cmb_sala_turno.configure(text_color=COR_PLACEHOLDER)
            self.cmb_sala_semestre.set("Semestre")
            self.cmb_sala_semestre.configure(text_color=COR_PLACEHOLDER)
        else: messagebox.showwarning("Erro", "Preencha dados.")

    def _del_sala(self):
        sel = self.tree_salas.selection()
        if sel:
            self.db.remover_sala(self.tree_salas.item(sel[0])['values'][0])
            self._filtrar_salas()

    def _on_select_sala(self, event):
        sel = self.tree_salas.selection()
        if sel:
            item = self.tree_salas.item(sel[0])['values']
            self.ent_sala_curso.delete(0, tk.END)
            self.ent_sala_curso.insert(0, item[0])
            
            self.cmb_sala_turno.set(item[1])
            self.cmb_sala_turno.configure(text_color=COR_TEXTO_PADRAO)

            self.ent_sala_local.delete(0, tk.END)
            self.ent_sala_local.insert(0, item[2])

if __name__ == "__main__":
    app = SistemaUnipApp()
    app.mainloop()