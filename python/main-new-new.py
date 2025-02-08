import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import openpyxl
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import os
import threading
import logging
import pyautogui

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoogleMessagesSender:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Google Messages Sender")
        self.root.geometry("600x600")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=1, fill="both")

        self.messages_tab = ttk.Frame(self.notebook)
        self.message_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.messages_tab, text="Google Messages")
        self.notebook.add(self.message_tab, text="Mensagens")

        self.setup_messages_tab()
        self.setup_message_tab()

        self.drivers = []
        self.phone_numbers = []
        self.base_user_data_dir = os.path.join(os.getcwd(), "google_messages_sessions")
        
        self.image_path = None
        
        self.auto_login()

    def auto_login(self):
        try:
            self.add_google_messages_instance()
        except Exception as e:
            logger.error(f"Erro ao fazer login automático: {str(e)}")
            messagebox.showerror("Erro de Login Automático", f"Não foi possível fazer o login automático: {str(e)}")

    def setup_messages_tab(self):
        add_instance_button = tk.Button(self.messages_tab, text="Conectar Google Messages", command=self.add_google_messages_instance)
        add_instance_button.pack(pady=5)
        
        self.instances_label = tk.Label(self.messages_tab, text="Instâncias ativas: 0")
        self.instances_label.pack(pady=5)

    def add_google_messages_instance(self):
        instance_id = len(self.drivers)
        user_data_dir = os.path.join(self.base_user_data_dir, f"instance_{instance_id}")
    
        chrome_options = Options()
        chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    
        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://messages.google.com/web/")
        
            messagebox.showinfo("Login", f"Faça login no Google Messages para a instância {instance_id + 1} e pressione OK quando estiver pronto.")
        
            WebDriverWait(driver, 300).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'mws-conversations-list'))
            )
        
            self.drivers.append(driver)
            self.update_instances_label()
            messagebox.showinfo("Login", f"Login realizado com sucesso para a instância {instance_id + 1}!")
        except Exception as e:
            logger.error(f"Erro ao iniciar o Google Messages: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao iniciar o Google Messages: {str(e)}")
            if driver:
                driver.quit()
            raise

    def update_instances_label(self):
        self.instances_label.config(text=f"Instâncias ativas: {len(self.drivers)}")

    def setup_message_tab(self):
        excel_button = tk.Button(self.message_tab, text="Carregar Excel", command=self.load_excel)
        excel_button.pack(pady=10)

        self.message_entry = tk.Text(self.message_tab, height=5, width=40)
        self.message_entry.pack(pady=10)

        image_button = tk.Button(self.message_tab, text="Selecionar Imagem", command=self.select_image)
        image_button.pack(pady=5)

        self.image_label = tk.Label(self.message_tab, text="Nenhuma imagem selecionada")
        self.image_label.pack(pady=5)

        preview_button = tk.Button(self.message_tab, text="Pré-visualizar Mensagem", command=self.preview_message)
        preview_button.pack(pady=5)

        send_button = tk.Button(self.message_tab, text="Enviar Mensagens", command=self.send_messages)
        send_button.pack(pady=10)

    def load_excel(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file_path:
            workbook = openpyxl.load_workbook(file_path)
            sheet = workbook.active
            self.phone_numbers = []
            for row in sheet.iter_rows(min_row=2, max_col=1):
                cell_value = row[0].value
                if cell_value is not None:
                    phone_number = str(cell_value).rstrip('.0')
                    phone_number = ''.join(filter(str.isdigit, phone_number))
                    if phone_number:
                        self.phone_numbers.append(phone_number)
            messagebox.showinfo("Excel Carregado", f"{len(self.phone_numbers)} números carregados")
            logger.info(f"Excel carregado: {len(self.phone_numbers)} números carregados")

    def select_image(self):
        self.image_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")])
        if self.image_path:
            self.image_label.config(text=f"Imagem selecionada: {os.path.basename(self.image_path)}")
        else:
            self.image_label.config(text="Nenhuma imagem selecionada")

    def preview_message(self):
        message = self.message_entry.get("1.0", tk.END).strip()
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Pré-visualização da Mensagem")
        
        preview_text = tk.Text(preview_window, height=10, width=50)
        preview_text.pack(pady=10)
        preview_text.insert(tk.END, message)
        preview_text.config(state=tk.DISABLED)

        if self.image_path:
            try:
                image = Image.open(self.image_path)
                image.thumbnail((200, 200))
                photo = ImageTk.PhotoImage(image)
                image_label = tk.Label(preview_window, image=photo)
                image_label.image = photo
                image_label.pack(pady=10)
            except Exception as e:
                logger.error(f"Erro ao carregar a imagem: {str(e)}")
                tk.Label(preview_window, text="Erro ao carregar a imagem").pack(pady=10)

    def send_messages(self):
        if not self.drivers:
            messagebox.showerror("Erro", "Conecte-se ao Google Messages primeiro")
            return
        
        if not self.phone_numbers:
            messagebox.showerror("Erro", "Carregue um arquivo Excel primeiro")
            return
        
        message = self.message_entry.get("1.0", tk.END).strip()
        if not message and not self.image_path:
            messagebox.showerror("Erro", "Digite uma mensagem ou selecione uma imagem")
            return

        chunks = [self.phone_numbers[i::len(self.drivers)] for i in range(len(self.drivers))]
        
        threads = []
        for i, chunk in enumerate(chunks):
            thread = threading.Thread(target=self.send_messages_chunk, args=(self.drivers[i], chunk, message))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        messagebox.showinfo("Concluído", "Envio de mensagens finalizado")

    def send_messages_chunk(self, driver, phone_numbers, message):
        failed_numbers = []
        for phone in phone_numbers:
            try:
                self.send_single_message(driver, phone, message)
                logger.info(f"Mensagem enviada para {phone}")
                time.sleep(random.uniform(15, 25))
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para {phone}: {str(e)}")
                failed_numbers.append(phone)

        if failed_numbers:
            logger.info(f"Tentando reenviar para {len(failed_numbers)} números que falharam...")
            time.sleep(25)
            for phone in failed_numbers:
                try:
                    self.send_single_message(driver, phone, message)
                    logger.info(f"Mensagem reenviada com sucesso para {phone}")
                    time.sleep(random.uniform(15, 25))
                except Exception as e:
                    logger.error(f"Falha ao reenviar para {phone}: {str(e)}")

    def send_single_message(self, driver, phone, message):
        try:
            self.navigate_to_new_conversation(driver)
            logger.info(f"Iniciando envio para {phone}")
            self.enter_recipient(driver, phone)
            self.check_page_state(driver)
            if message:
                self.enter_message(driver, message)
            if self.image_path:
                self.attach_image(driver)
            self.check_page_state(driver)
            
            # Adicionar ID ao botão de envio
            self.add_id_to_send_button(driver)
            
            self.click_send_button(driver)
            if not self.verify_message_sent(driver):
                raise Exception("Falha na verificação do envio da mensagem")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {phone}: {str(e)}")
            self.capture_screenshot(driver, f"erro_envio_{phone}")
            raise

    def navigate_to_new_conversation(self, driver):
        logger.info("Navegando para nova conversa")
        driver.get("https://messages.google.com/web/conversations/new")
        self.wait_for_page_load(driver)
        self.capture_screenshot(driver, "nova_conversa")
        logger.info("Página de nova conversa carregada")

    def wait_for_page_load(self, driver):
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def enter_recipient(self, driver, phone):
        logger.info(f"Inserindo destinatário: {phone}")
        try:
            recipient_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Digite um nome, número de telefone ou endereço de e-mail"]'))
            )
            
            recipient_input.clear()
            
            for digit in phone:
                recipient_input.send_keys(digit)
                time.sleep(0.1)
            
            time.sleep(2)
            
            recipient_input.send_keys(Keys.ENTER)
            
            time.sleep(2)
            
            logger.info("Destinatário inserido com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inserir destinatário: {str(e)}")
            self.capture_screenshot(driver, f"erro_destinatario_{phone}")
            raise

    def enter_message(self, driver, message):
        logger.info("Inserindo mensagem")
        message_input = None
        try:
            message_input = self.wait_for_clickable_element(driver, 'textarea[placeholder="Mensagem RCS"], textarea[placeholder="Envio de mensagens"]', timeout=10)
        except TimeoutException:
            logger.error("Ambos os seletores falharam. Não foi possível encontrar o campo de mensagem.")
            self.capture_screenshot(driver, "erro_campo_mensagem")
            raise Exception("Campo de mensagem não encontrado")

        if message_input:
            message_input.clear()
            lines = message.split('\n')
            for i, line in enumerate(lines):
                message_input.send_keys(line)
                if i < len(lines) - 1:
                    message_input.send_keys(Keys.SHIFT + Keys.ENTER)
            time.sleep(2)
            logger.info("Mensagem inserida")
        else:
            logger.error("Campo de mensagem não encontrado após tentativas")
            raise Exception("Campo de mensagem não encontrado")

    def attach_image(self, driver):
        logger.info("Tentando anexar imagem")
        try:
            attach_button = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button[aria-label="Selecionar anexos"][data-e2e-picker-button="ATTACHMENT"]'))
            )

            self.focus_element(driver, attach_button)

            try:
                attach_button.click()
            except Exception:
                logger.warning("Clique normal falhou, tentando com JavaScript")
                driver.execute_script("arguments[0].click();", attach_button)

            time.sleep(2)
            pyautogui.press('esc')
            time.sleep(1)

            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
            )
            
            file_input.send_keys(self.image_path)
            
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'mws-message-image-preview'))
            )
            
            logger.info("Imagem anexada com sucesso")
        except TimeoutException:
            logger.error("Tempo excedido ao tentar anexar a imagem")
            self.capture_screenshot(driver, "erro_timeout_anexo_imagem")
            raise Exception("Não foi possível anexar a imagem: tempo excedido")
        except Exception as e:
            logger.error(f"Erro ao anexar imagem: {str(e)}")
            self.capture_screenshot(driver, "erro_anexo_imagem")
            raise

    def is_button_clickable(self, driver):
        try:
            send_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-e2e-send-text-button]'))
            )
            return send_button.is_enabled() and send_button.is_displayed()
        except:
            return False

    def add_id_to_send_button(self, driver, custom_id="meu-botao-enviar"):
        script = """
        var button = document.querySelector('button[data-e2e-send-text-button]');
        if (button) {
            button.id = arguments[0];
            return true;
        }
        return false;
        """
        success = driver.execute_script(script, custom_id)
        if success:
            logger.info(f"ID '{custom_id}' adicionado ao botão de envio com sucesso")
        else:
            logger.warning("Não foi possível adicionar ID ao botão de envio")
        return success

    def click_send_button(self, driver):
        logger.info("Tentando enviar a mensagem")
        try:
            self.check_page_state(driver)

            if not self.is_button_clickable(driver):
                logger.warning("O botão de envio não está clicável")
                self.capture_screenshot(driver, "botao_nao_clicavel")
                raise Exception("Botão de envio não está clicável")

            send_methods = [
                self.send_with_custom_id,
                self.send_with_selenium_click,
                self.send_with_javascript,
            ]

            for method in send_methods:
                try:
                    method(driver)
                    if self.verify_message_sent(driver):
                        logger.info(f"Mensagem enviada com sucesso usando {method.__name__}")
                        return
                except Exception as e:
                    logger.warning(f"Falha ao enviar mensagem com {method.__name__}: {str(e)}")

            raise Exception("Todas as tentativas de envio falharam")

        except Exception as e:
            logger.error(f"Erro ao enviar a mensagem: {str(e)}")
            self.capture_screenshot(driver, "erro_envio_mensagem")
            raise

    def send_with_custom_id(self, driver):
        try:
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "meu-botao-enviar"))
            )
            send_button.click()
            logger.info("Botão de envio clicado com sucesso usando ID personalizado")
        except Exception as e:
            logger.error(f"Erro ao clicar no botão de envio usando ID personalizado: {str(e)}")
            raise

    def send_with_selenium_click(self, driver):
        try:
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-e2e-send-text-button].send-button'))
            )
            send_button.click()
            logger.info("Botão de envio clicado com sucesso usando seletor CSS específico")
        except Exception as e:
            logger.error(f"Erro ao clicar no botão de envio: {str(e)}")
            raise

    def send_with_javascript(self, driver):
        try:
            driver.execute_script("""
                var buttons = document.querySelectorAll('button[data-e2e-send-text-button].send-button');
                if (buttons.length > 0) {
                    buttons[0].click();
                } else {
                    throw new Error('Botão de envio não encontrado');
                }
            """)
            logger.info("Botão de envio clicado com sucesso usando JavaScript")
        except Exception as e:
            logger.error(f"Erro ao clicar no botão de envio com JavaScript: {str(e)}")
            raise

    def verify_message_sent(self, driver):
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "mws-message-status-row[status='SENT']"))
            )
            return True
        except TimeoutException:
            return False

    def check_page_state(self, driver):
        logger.info("Verificando o estado da página")
        try:
            message_field = driver.find_elements(By.CSS_SELECTOR, 'textarea[placeholder="Mensagem RCS"], textarea[placeholder="Envio de mensagens"]')
            if message_field:
                logger.info("Campo de mensagem encontrado")
            else:
                logger.warning("Campo de mensagem não encontrado")

            send_button = driver.find_elements(By.CSS_SELECTOR, 'button[data-e2e-send-text-button]')
            if send_button:
                logger.info("Botão de envio encontrado")
            else:
                logger.warning("Botão de envio não encontrado")

            overlay = driver.find_elements(By.CSS_SELECTOR, '.modal, .overlay, .dialog')
            if overlay:
                logger.warning("Possível pop-up ou overlay detectado")
            else:
                logger.info("Nenhum pop-up ou overlay detectado")

            self.capture_screenshot(driver, "page_state_check")

        except Exception as e:
            logger.error(f"Erro ao verificar o estado da página: {str(e)}")

    def wait_for_element(self, driver, selector, timeout=30):
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def wait_for_clickable_element(self, driver, selector, timeout=30):
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )

    def focus_element(self, driver, element):
        try:
            driver.execute_script("arguments[0].focus();", element)
            time.sleep(0.5)
            actions = ActionChains(driver)
            actions.move_to_element(element).perform()
            time.sleep(0.5)
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            actions.move_to_element(element).click_and_hold().release().perform()
            time.sleep(0.5)
            logger.info("Foco dado ao elemento com sucesso")
        except Exception as e:
            logger.error(f"Erro ao tentar dar foco ao elemento: {str(e)}")

    def capture_screenshot(self, driver, name):
        screenshot_path = f"{name}_{int(time.time())}.png"
        driver.save_screenshot(screenshot_path)
        logger.info(f"Screenshot capturada: {screenshot_path}")

    def on_closing(self):
        for driver in self.drivers:
            driver.quit()
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

# Criação e execução da aplicação
if __name__ == "__main__":
    app = GoogleMessagesSender()
    app.run()