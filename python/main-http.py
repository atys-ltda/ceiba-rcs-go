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
import requests
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoogleMessagesSender:
    MESSAGE_CREATED = 1
    MESSAGE_TRYING_RCS = 2
    MESSAGE_SENDED_RCS = 3
    MESSAGE_ONLY_SMS = 4
    MESSAGE_TRYING_SMS = 5
    MESSAGE_SENDED_SMS = 6
    MESSAGE_FAILED = 7
    
    WORKER = 3

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Google Messages Sender")
        self.root.geometry("600x600")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=1, fill="both")

        self.messages_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.messages_tab, text="Google Messages")

        self.credit = tk.BooleanVar(value=False)
        
        self.setup_messages_tab()

        self.drivers = []
        self.phone_numbers = []
        self.base_user_data_dir = os.path.join(os.getcwd(), "google_messages_sessions")
        
        self.image_path = None
        self.access_token = ""
        self.user_data = False
        
        self.auto_login()

    def auto_login(self):
        try:
            self.add_google_messages_instance()
        except Exception as e:
            logger.error(f"Erro ao fazer login automático: {str(e)}")
            messagebox.showerror("Erro de Login Automático", f"Não foi possível fazer o login automático: {str(e)}")

    def setup_messages_tab(self):
        # 1. autenticar a aplicação
        first_steep_label = tk.Label(self.messages_tab, text="Passo 1. Autenticar este worker")
        first_steep_label.pack(pady=5)

        app_email_label = tk.Label(self.messages_tab, text="Email do worker")
        app_email_label.pack(pady=5)        
        self.app_email = tk.Entry(self.messages_tab)
        self.app_email.pack(pady=1)

        app_password_label = tk.Label(self.messages_tab, text="Senha do worker")
        app_password_label.pack(pady=5)        
        self.app_password = tk.Entry(self.messages_tab)
        self.app_password.pack(pady=5)

        self.add_login_button = tk.Button(self.messages_tab, text="Login", command=self.app_login)
        self.add_login_button.pack(pady=5)
        self.app_login_label = tk.Label(self.messages_tab, text="")
        self.app_login_label.pack(pady=5)

        # 2. telefones com crédito
        second_steep_label = tk.Label(self.messages_tab, text="Passo 2. Os chips a usar tem crédito?")
        second_steep_label.pack(pady=5)
        radio_nao = tk.Radiobutton(self.messages_tab, text="Não", variable=self.credit, value=False)
        radio_nao.pack()
        radio_sim = tk.Radiobutton(self.messages_tab, text="Sim", variable=self.credit, value=True)
        radio_sim.pack()        

        # 2. conectar com Google
        second_steep_label = tk.Label(self.messages_tab, text="Passo 3. Conecte várias contas do Google Menssages")
        second_steep_label.pack(pady=5)
        add_instance_button = tk.Button(self.messages_tab, text="Conectar Google Messages", command=self.add_google_messages_instance)
        add_instance_button.pack(pady=5)        
        self.instances_label = tk.Label(self.messages_tab, text="Instâncias ativas: 0")
        self.instances_label.pack(pady=5)

        # 3. inicie o envio das mensagens
        third_steep_label = tk.Label(self.messages_tab, text="Passo 4. Inicie o envio das mensagens.")
        third_steep_label.pack(pady=5)
        self.send_button = tk.Button(self.messages_tab, text="Enviar Mensagens", command=self.send_messages_infinitely)
        self.send_button.pack(pady=10)
        
    def app_login(self):
        self.access_token = ""
        email = self.app_email.get().strip()
        password = self.app_password.get().strip()

        if email == "" or password == "":
            messagebox.showerror("Atenção", "Digite corretamente o usuário e senha deste Worker")
            return
        
        url = "https://rcs-back.atys.pro/api/oauth/token"
        payload = json.dumps({
          "email": email,
          "password": password,
          "grant_type": "password"
        })
        headers = {
          'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            resposta_json = response.json()
            self.user_data = resposta_json.get("user_data", {})            
            if self.user_data.get('role_id') == self.WORKER:
                self.access_token = resposta_json.get("access_token")
                self.app_login_label.config(text="Usuário autenticado", fg="green")
                self.app_email.config(state="disabled")
                self.app_password.config(state="disabled")
                self.add_login_button.config(state="disabled")
            else:
                self.app_login_label.config(text="Usuário não autorizado", fg="red")
        else:
            self.app_login_label.config(text="Falha no login: credenciais inválidas", fg="red")

    def add_google_messages_instance(self):
        if self.access_token == "":
            messagebox.showerror("Erro", "Worker não autenticado, realize o login no Passo 1")
            return
        
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

    def send_messages_infinitely(self):
        if self.access_token == "":
            messagebox.showerror("Erro", "Worker não autenticado, realize o login no Passo 1")
            return
        if not self.drivers:
            messagebox.showerror("Erro", "Conecte-se ao Google Messages primeiro")
            return
        self.send_button.config(state="disabled")
        while True:
            logger.info("Enviando mensagens")
            self.send_messages()

    def send_messages(self):
        if not self.credit.get():
            status_id = self.MESSAGE_CREATED
        else:
            status_id = self.MESSAGE_ONLY_SMS

        url = f"https://rcs-back.atys.pro/api/get-campaign-messages?status_id={status_id}"
        payload = ""
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.request("GET", url, headers=headers, data=payload)

        if response.status_code == 200:
            resposta_json = response.json()
            self.messages = resposta_json.get("messages", {})
            print(f"Foram obtidos {len(self.messages)} mensagens do servidor para serem enviados")
            campaign = resposta_json.get("campaign", {})
            if campaign:
                self.text_message = campaign.get("message")
        else:        
            if response.status_code == 401:
                messagebox.showerror("Erro", "Worker não autenticado, realize o login no Passo 1")
                return
            else:
                messagebox.showerror("Erro", f"Erro {response.status_code}: {response.text}")
                print(f"Erro {response.status_code}: {response.text}")
                return
            
        if len(self.messages):
            messages_chunks = [self.messages[i::len(self.drivers)] for i in range(len(self.drivers))]
            threads = []
            hasCredit = self.credit.get()
            for i, messages_chunk in enumerate(messages_chunks):
                thread = threading.Thread(target=self.send_messages_chunk, args=(self.drivers[i], messages_chunk, self.text_message, hasCredit))
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()
            logger.info("Concluído. Envio de mensagens finalizado")
        else:
            time.sleep(1 * 60)

    def send_messages_chunk(self, driver, messages_chunk, text_message, hasCredit):
        failed_messages = 0
        logger.info(f"O chunk atual tem {len(messages_chunk)} mensagens")
        for message in messages_chunk:
            try:
                self.send_single_message(driver, message, text_message)
                logger.info(f"Mensagem enviada para {message.get('contact').get('phone')}")
                if not hasCredit:
                    message['status_id'] = self.MESSAGE_SENDED_RCS
                else: 
                    message['status_id'] = self.MESSAGE_SENDED_SMS
                # time.sleep(random.uniform(45, 60))
            except Exception as e:
                failed_messages = failed_messages + 1
                message['status_id'] = self.MESSAGE_FAILED
                if not hasCredit:
                    message['status_id'] = self.MESSAGE_ONLY_SMS
                else: 
                    message['status_id'] = self.MESSAGE_FAILED
                logger.error(f"Erro enviando mensagem para {message.get('contact').get('phone')}: {str(e)}")
        
        url = "https://rcs-back.atys.pro/api/update-campaign-processed-messages"
        payload = json.dumps({
          "messages": messages_chunk
        })        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=payload)
        logger.info("Requisição update-campaign-processed-messages de atualização feita com secesso após processar um chunk de mensagens")

    def send_single_message(self, driver, message, text_message):
        try:
            self.navigate_to_new_conversation(driver)
            logger.info(f"Iniciando envio para {message.get('contact').get('phone')}")
            self.enter_recipient(driver, message.get('contact').get('phone'))
            self.check_page_state(driver)
            if message:
                self.enter_message(driver, text_message)
            # if self.image_path:
            #     self.attach_image(driver)
            self.check_page_state(driver)
            
            if not self.click_send_button(driver):
                if not self.message_was_not_sent_try_again(driver):
                    raise Exception("Falha na verificação do envio da mensagem por message_was_not_sent_try_again")
                if not self.verify_message_sent(driver):
                    raise Exception("Falha na verificação do envio da mensagem por verify_message_sent")

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {message.get('contact').get('phone')}: {str(e)}")
            self.capture_screenshot(driver, f"erro_envio_{message.get('contact').get('phone')}")
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

    def click_send_button(self, driver):
        logger.info("Tentando enviar a mensagem")
        try:
            self.check_page_state(driver)

            # Verifica se o botão está clicável
            if not self.is_button_clickable(driver):
                logger.warning("O botão de envio não está clicável")
                self.capture_screenshot(driver, "botao_nao_clicavel")
                raise Exception("Botão de envio não está clicável")

            send_methods = [
                self.send_with_ripple_effect,
                self.send_with_selenium_click,
                self.send_with_javascript,
                self.send_with_action_click,
                self.send_with_svg_click,
                self.send_with_aria_label,
                self.send_with_pyautogui,
            ]

            for method in send_methods:
                try:
                    method(driver)
                    if self.verify_message_sent(driver):
                        logger.info(f"Mensagem enviada com sucesso usando {method.__name__}")
                        return True
                    if self.message_was_not_sent_try_again(driver):
                        logger.error(f"A mensagem não foi enviada. Clique para tentar novamente. {method.__name__}")
                        return False
                except Exception as e:
                    logger.warning(f"Falha ao enviar mensagem com {method.__name__}")
            raise Exception("Todas as tentativas de envio falharam")

        except Exception as e:
            logger.error(f"Erro ao enviar a mensagem: {str(e)}")
            self.capture_screenshot(driver, "erro_envio_mensagem")
            raise

    def send_with_ripple_effect(self, driver):
        try:
            # Localiza o botão de envio
            send_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-e2e-send-text-button]'))
            )

            # Localiza o elemento de ripple dentro do botão
            ripple_element = send_button.find_element(By.CSS_SELECTOR, '.mat-ripple.mat-mdc-button-ripple')

            # Usa JavaScript para simular o efeito de ripple
            driver.execute_script("""
                var ripple = arguments[0];
                var event = new MouseEvent('mousedown', {
                    view: window,
                    bubbles: true,
                    cancelable: true
                });
                ripple.dispatchEvent(event);
            """, ripple_element)

            # Espera um curto período para o efeito visual
            time.sleep(0.1)

            # Clica no botão
            send_button.click()

            logger.info("Botão de envio clicado com sucesso usando simulação de ripple send_with_ripple_effect")
        except Exception as e:
            logger.error(f"Exception ao clicar no botão de envio com simulação de ripple send_with_ripple_effect")
            # logger.error(f"Erro ao clicar no botão de envio com simulação de ripple send_with_ripple_effect: {str(e)}")
            raise

    def send_with_selenium_click(self, driver):
        try:
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-e2e-send-text-button].send-button'))
            )
            send_button.click()
            logger.info("Botão de envio clicado com sucesso usando seletor CSS específico send_with_selenium_click")
        except Exception as e:
            logger.error(f"Erro ao clicar no botão de envio send_with_selenium_click: {str(e)}")
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
            logger.info("Botão de envio clicado com sucesso usando JavaScript send_with_javascript")
        except Exception as e:
            logger.error(f"Erro ao clicar no botão de envio com JavaScript send_with_javascript: {str(e)}")
            raise

    def send_with_action_click(self, driver):
        try:
            send_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-e2e-send-text-button].send-button'))
            )
            ActionChains(driver).move_to_element(send_button).click().perform()
            logger.info("Botão de envio clicado com sucesso usando ActionChains send_with_action_click")
        except Exception as e:
            logger.error(f"Erro ao clicar no botão de envio com ActionChains send_with_action_click: {str(e)}")
            raise

    def send_with_svg_click(self, driver):
        try:
            svg = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-e2e-send-text-button] svg'))
            )
            svg.click()
            logger.info("Ícone SVG do botão de envio clicado com sucesso send_with_svg_click")
        except Exception as e:
            logger.error(f"Erro ao clicar no ícone SVG do botão de envio send_with_svg_click: {str(e)}")
            raise

    def send_with_aria_label(self, driver):
        try:
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Enviar SMS"]'))
            )
            send_button.click()
            logger.info("Botão de envio clicado com sucesso usando aria-label send_with_aria_label")
        except Exception as e:
            logger.error(f"Erro ao clicar no botão de envio usando aria-label send_with_aria_label: {str(e)}")
            raise

    def send_with_pyautogui(self, driver):
        try:
            # Pressiona a tecla Enter do teclado numérico
            pyautogui.press('enter')
            time.sleep(0.5)
            pyautogui.press('num enter')
            logger.info("Tecla Enter do teclado numérico pressionada send_with_pyautogui")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Erro ao pressionar Enter do teclado numérico com PyAutoGUI send_with_pyautogui: {str(e)}")
            raise

    def verify_message_sent(self, driver):
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "mws-message-status-row[status='SENT']"))
            )
            return True
        except TimeoutException:
            return False
        
    def message_was_not_sent_try_again(self, driver):
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span.failed.ng-star-inserted'))
            )
            return True
        except:
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