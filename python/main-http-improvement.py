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
import requests
import json
import asyncio
# import win32clipboard
# from io import BytesIO
import time

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class GoogleMessagesSender:
    MESSAGE_CREATED = 1
    MESSAGE_TRYING_RCS = 2
    MESSAGE_SENDED_RCS = 3
    MESSAGE_ONLY_SMS = 4
    MESSAGE_TRYING_SMS = 5
    MESSAGE_SENDED_SMS = 6
    MESSAGE_FAILED = 7
    ROLE_WORKER = 3

    MESSAGE_NOT_SENDED = 0
    MESSAGE_SENDED = 1
    UNABLE_NEW_CONVERSATION = 2
    UNABLE_ENTER_RECIPIENT = 3
    UNABLE_FIND_TEXTAREA = 4

    # principal functions
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
        self.enabled_instances = []
        self.phone_numbers = []
        self.base_user_data_dir = os.path.join(os.getcwd(), "google_messages_sessions")        
        self.image_path = None
        self.access_token = ""
        self.user_data = False

    def setup_messages_tab(self):
        # 1. autenticar a aplicação
        first_steep_label = tk.Label(self.messages_tab, text="Passo 1. Autenticar este worker")
        first_steep_label.pack(pady=5)

        app_email_label = tk.Label(self.messages_tab, text="Email do worker")
        app_email_label.pack(pady=5)        
        self.app_email = tk.Entry(self.messages_tab)
        self.app_email.insert(0, "worker1@gmail.com")
        self.app_email.pack(pady=1)

        app_password_label = tk.Label(self.messages_tab, text="Senha do worker")
        app_password_label.pack(pady=5)        
        self.app_password = tk.Entry(self.messages_tab)
        self.app_password.insert(0, "12345678")
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

        # 3. conectar com Google
        second_steep_label = tk.Label(self.messages_tab, text="Passo 3. Conecte várias contas do Google Menssages")
        second_steep_label.pack(pady=5)
        self.add_instance_button = tk.Button(self.messages_tab, text="Conectar Google Messages", command=self.add_google_messages_instance)
        self.add_instance_button.pack(pady=5)        
        self.instances_label = tk.Label(self.messages_tab, text="Instâncias ativas: 0")
        self.instances_label.pack(pady=5)

        # 4. inicie o envio das mensagens
        third_steep_label = tk.Label(self.messages_tab, text="Passo 4. Inicie o envio das mensagens.")
        third_steep_label.pack(pady=5)
        self.send_button = tk.Button(self.messages_tab, text="Enviar Mensagens", command=self.send_messages_infinitely)
        self.send_button.pack(pady=10)

         # 5. Adicionar botão de encerramento
        exit_button = tk.Button(self.messages_tab, text="Encerrar Aplicação", command=self.on_closing)
        exit_button.pack(pady=10)
        
    def app_login(self):
        self.access_token = ""
        email = self.app_email.get().strip()
        password = self.app_password.get().strip()
        if email == "" or password == "":
            messagebox.showerror("Atenção", "Digite corretamente o usuário e senha deste Worker")
            return
        
        url = "https://rcs-back.atys.pro/api/oauth/token"
        payload = json.dumps({"email": email, "password": password, "grant_type": "password"})
        headers = { 'Content-Type': 'application/json' }
        response = requests.request("POST", url, headers=headers, data=payload)

        if response.status_code == 200:
            resposta_json = response.json()
            self.user_data = resposta_json.get("user_data", {})            
            if self.user_data.get('role_id') == self.ROLE_WORKER:
                self.access_token = resposta_json.get("access_token")
                self.app_login_label.config(text=f"Usuário {self.app_email} autenticado", fg="green")
                self.app_email.config(state="disabled")
                self.app_password.config(state="disabled")
                self.add_login_button.config(state="disabled")
                self.worker_name = self.app_email.get().strip().split('@')[0]
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
        
            messagebox.showinfo("Login", f"Faça login no Google Messages para a instância {instance_id + 1}. \nPressione OK somente quando estiver pronto.")
        
            WebDriverWait(driver, 300).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'mws-conversations-list'))
            )
        
            self.drivers.append(driver)
            self.enabled_instances.append(0) # [0, 0, 1629845689, 0, 0]
            self.instances_label.config(text=f"Instâncias ativas: {len(self.drivers)}")
            messagebox.showinfo("Login", f"Login realizado com sucesso para a instância {instance_id + 1}!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar o Google Messages: {str(e)}")
            if driver:
                driver.quit()
            raise

    def send_messages_infinitely(self):
        if self.access_token == "":
            messagebox.showerror("Erro", "Worker não autenticado, realize o login no Passo 1")
            return
        if not self.drivers:
            messagebox.showerror("Erro", "Conecte-se ao Google Messages primeiro")
            return
        self.add_instance_button.config(state="disabled")
        self.send_button.config(state="disabled")
        self.running = True
        threading.Thread(target=self.run_message_loop, args=(), daemon=True).start()

    def run_message_loop(self):
        while self.running:
            self.send_messages()          
            if not self.running:
                break

    def send_messages(self):
        logger.info(f"Worker {self.worker_name}, info: requesting new messages from server.")
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
            logger.info(f"Worker {self.worker_name}, info: where obtained {len(self.messages)} messages from server.")
            campaign = resposta_json.get("campaign", {})
            if campaign:
                self.text_message = campaign.get("message")
        else:        
            if response.status_code == 401:
                messagebox.showerror("Erro", "Worker não autenticado, realize o login no Passo 1")
                logger.error(f"Worker {self.worker_name}, info: worker is unlogged.")
                return
            else:
                messagebox.showerror("Erro", f"Erro {response.status_code}: {response.text}")
                logger.error(f"Worker {self.worker_name}, info: error requesting messages, http code {response.status_code}, server response {response.text}.")
                return
            
        if len(self.messages):
            # messages_chunks = [self.messages[i::len(self.drivers)] for i in range(len(self.drivers))]
            for i in range(len(self.enabled_instances)):
                if (time.time() - self.enabled_instances[i]) / 1800 > 1:
                    logger.info(f"Worker {self.worker_name}, instance {i}, has been unlocked after sleep 1/2 hour.")
                    self.enabled_instances[i] = 0
    
            num_zeros = self.enabled_instances.count(0)
            messages_chunks = [self.messages[i::num_zeros] for i in range(num_zeros)]
            threads = []
            has_credit = self.credit.get()

            flag = False
            for i, messages_chunk in enumerate(messages_chunks):
                if self.enabled_instances[i] == 0:
                    flag = True
                    thread = threading.Thread(target=self.send_messages_chunk, args=(self.drivers[i], messages_chunk, self.text_message, has_credit, i))
                    threads.append(thread)
                    thread.start()

            for thread in threads:
                thread.join()

            if not flag:
                logger.info(f"Worker {self.worker_name}, info: worker is sleeping 25 minutes because all drivers are unable.")
                time.sleep(25 * 60)
            logger.info(f"Worker {self.worker_name}, info: messages were processed, all threads are finished.")
        else:
            time.sleep(5 * 60)

    def send_messages_chunk(self, driver, messages_chunk, text_message, has_credit, i):
        logger.info(f"Worker {self.worker_name}, instance {i}, info: actual chunk length is {len(messages_chunk)}.")
        for j, message in enumerate(messages_chunk):
            resp = self.send_single_message(driver, message, text_message, i)
            
            if resp == self.MESSAGE_NOT_SENDED:
                if not has_credit:
                    message['status_id'] = self.MESSAGE_ONLY_SMS
                    logger.info(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: message {message.get('id') } will be tryied as SMS.")
                else: 
                    message['status_id'] = self.MESSAGE_FAILED
                    logger.error(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: message {message.get('id') } has failed.")
            elif resp == self.MESSAGE_SENDED:
                if not has_credit:
                    message['status_id'] = self.MESSAGE_SENDED_RCS
                    logger.info(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: message {message.get('id') } was sended as RCS.")
                else: 
                    message['status_id'] = self.MESSAGE_SENDED_SMS
                    logger.info(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: message {message.get('id') } was sended as SMS.")
            elif resp == self.UNABLE_NEW_CONVERSATION or resp == self.UNABLE_ENTER_RECIPIENT:
                time.sleep(15) # ainda não sei o que fazer nestes dois caso
            elif resp == self.UNABLE_FIND_TEXTAREA:
                self.enabled_instances[i] = time.time()
                logger.info(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: message {message.get('id') } this instance will be lock by UNABLE_FIND_TEXTAREA.")
                for k in range(j, len(messages_chunk)):
                    messages_chunk[k]['status_id'] = 1
                break
        self.sincronize_message_status(messages_chunk, i)

    def send_single_message(self, driver, message, text_message, i):
        logger.info(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: starting sending message -------------------------------------------------------.")
        try:
            self.navigate_to_new_conversation(driver)
        except Exception:
            logger.error(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: UNABLE_NEW_CONVERSATION.")
            self.capture_screenshot(driver, "error_send_single_message")
            return self.UNABLE_NEW_CONVERSATION
        logger.info(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: new conversation page loaded.")
        
        try:
            self.enter_recipient(driver, message.get('contact').get('phone'))
        except Exception:
            logger.error(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: UNABLE_ENTER_RECIPIENT.")
            self.capture_screenshot(driver, "error_enter_recipient")
            return self.UNABLE_ENTER_RECIPIENT
        logger.info(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: recipient entered.")
        
        time.sleep(2)
        # self.check_page_state(driver)

        try:
            driver.find_element(By.XPATH, "//*[contains(text(), 'Aguarde antes de criar mais conversas.')]")
            logger.error(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: UNABLE_FIND_TEXTAREA by Aguarde antes de criar mais conversas.")
            self.capture_screenshot(driver, "UNABLE_FIND_TEXTAREA_by_Aguarde_antes_de_criar_mais_conversas")
            return self.UNABLE_FIND_TEXTAREA
        except Exception:
            pass

        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.input"))
            )
            textarea = driver.find_element(By.CSS_SELECTOR, "textarea.input")
            text = textarea.get_attribute("aria-label")
        except Exception as e:
            self.capture_screenshot(driver, "UNABLE_FIND_TEXTAREA_by_CSS_SELECTOR")
            logger.error(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: UNABLE_FIND_TEXTAREA by CSS_SELECTOR. Exception is: {str(e.__traceback__)}")
            return self.UNABLE_FIND_TEXTAREA
        
        is_rcs = False
        if "RCS" in text:
            is_rcs = True
        
        if not self.credit.get() and not is_rcs:
            logger.info(f"Worker {self.worker_name}, instance {i}, phone {message.get('contact').get('phone')}, info: unable to send RCS to this contact *********.")
            time.sleep(5)
            return self.MESSAGE_NOT_SENDED

        # if self.image_path:
        #     asyncio.run(self.send_image(driver, "", self.image_path))
        
        if message:
            if asyncio.run(self.send_message(driver, text_message)):
                time.sleep(12)
                return self.MESSAGE_SENDED
            else:
                return self.MESSAGE_NOT_SENDED

        # if message:
        #     if not asyncio.run(self.send_message(driver, text_message)):
        #         return False           
        # if self.verify_message_sent(driver):
        #     return True            
        # if self.message_was_not_sent_try_again(driver): # only trying SMS without credit
        #     return False            
        # return True
        
    async def send_message(self, driver, message):
        try:
            input_field = driver.find_element(By.CSS_SELECTOR, "textarea.input")
            lines = message.split('\n')
            for i, line in enumerate(lines):
                input_field.send_keys(line)
                if i < len(lines) - 1:
                    input_field.send_keys(Keys.SHIFT + Keys.ENTER)
                await asyncio.sleep(0.1)
            input_field.send_keys(Keys.ENTER)
            return True
        except Exception:
            return False
        
    '''
    async def send_image(self, driver, caption, file_path):
        try:
            self.copy_file_to_clipboard(file_path)
            driver.find_element(By.CSS_SELECTOR, "textarea.input").send_keys(Keys.CONTROL, 'v')
            await asyncio.sleep(5)
            driver.find_element(By.CSS_SELECTOR, "textarea.input").send_keys(caption + Keys.ENTER)
            logger.info("Imagem enviada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao enviar imagem: {e}")
            raise
        
    def copy_file_to_clipboard(self, file_path):
        image = Image.open(file_path)
        output = BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
    '''

    # auxiliar functions
    def navigate_to_new_conversation(self, driver):
        driver.get("https://messages.google.com/web/conversations/new")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def enter_recipient(self, driver, phone):
        try:
            recipient_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Digite um nome, número de telefone ou endereço de e-mail"]'))
            )
            recipient_input.clear()
            
            for digit in phone:
                recipient_input.send_keys(digit)
                time.sleep(0.1)
            recipient_input.send_keys(Keys.ENTER)
            time.sleep(1)
        except Exception as e:
            raise Exception(f"error entering recipient, exception is: {str(e)}")

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
        try:

            message_field = driver.find_elements(By.CSS_SELECTOR, 'textarea[placeholder="Mensagem RCS"], textarea[placeholder="Envio de mensagens"]')
            if not message_field:
                raise Exception("missing textarea field")

            send_button = driver.find_elements(By.CSS_SELECTOR, 'button[data-e2e-send-text-button]')
            if not send_button:
                raise Exception("missing send-text-button")

            overlay = driver.find_elements(By.CSS_SELECTOR, '.modal, .overlay, .dialog')
            if overlay:
                raise Exception("pop-up or overlay detected")
        except Exception as e:
            raise e
    
    def sincronize_message_status(self, messages_chunk, i):
        url = "https://rcs-back.atys.pro/api/update-campaign-processed-messages"
        payload = json.dumps({
          "messages": messages_chunk
        })        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            'Content-Type': 'application/json'
        }
        requests.post(url, headers=headers, data=payload)
        logger.info(f"Worker {self.worker_name}, instance {i}, info: status of messages has been updated on the server.")

    def capture_screenshot(self, driver, name):
        screenshot_path = f"{name}_{int(time.time())}.png"
        driver.save_screenshot(screenshot_path)
        logger.info(f"Screenshot capturada: {screenshot_path}")

    def on_closing(self):
        for driver in self.drivers:
            driver.quit()
        self.running = False
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    app = GoogleMessagesSender()
    app.run()