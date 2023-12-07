import os, sys, json, time, logging
from datetime import datetime
from telethon.sync import TelegramClient
from telethon import functions, types, password, errors

SESSIONS_DIRECTORY = "./sessions/"
USERNAMES_PATH = "./usernames.txt"
LOGS_PATH = "./logs.log"

logging.basicConfig(filename=LOGS_PATH, level=logging.INFO, format='%(asctime)s - %(message)s')

processed_accounts = 0
added_usernames = 0
skipped_usernames = 0

processed_accounts = 0
added_usernames = 0
skipped_usernames = 0

def log_statistics():
    global processed_accounts, added_usernames, skipped_usernames

    log_message("***** ИТОГОВЫЙ ОТЧЕТ *****")
    log_message(f"Дата старта: {start_time}")
    log_message(f"Дата окончания: {datetime.now()}")
    log_message(f"Обработано аккаунтов: {processed_accounts}")
    log_message(f"Добавлено юзернеймов: {added_usernames}")
    log_message(f"Пропущено юзернеймов: {skipped_usernames}")
    log_message("**************************")

def log_message(message, account_username=None, added_username=None, skipped_username=None):
    log_entry = f"{datetime.now()} - {message}"
    print(log_entry)
    logging.info(log_entry)

    if account_username:
        log_message(f"Аккаунт {account_username} завершил работу.")
    if added_username:
        log_message(f"Добавлен юзернейм: {added_username}")
        added_usernames += 1
    if skipped_username:
        log_message(f"Пропущен юзернейм: {skipped_username}")
        skipped_usernames += 1

def check_files_exist(path, files):
    all_files_exist = True

    for file_name in files:
        full_path = os.path.join(path, file_name)
        if not os.path.exists(full_path):
            all_files_exist = False

    return all_files_exist

def auth(full_path_to_session, data):
    api_id, api_hash, two_fa = data

    try:
        client = TelegramClient(full_path_to_session, api_id, api_hash)
        client.connect()

        if not client.is_user_authorized():
            client.send_code_request(phone)
            try:
                client.sign_in(phone, input('Введите код, который прислал телеграм: '))
            except errors.SessionPasswordNeededError:
                client.sign_in(password=two_fa)

    except ConnectionError:
        log_message("Программа завершает работу. Требуется сменить api_hash, api_id")
        sys.exit("Программа завершает работу. Требуется сменить api_hash, api_id")

    log_message("Успешная авторизация.")
    return client

def find_json_files(directory_path, excluded_phone):
    session_files = [file_name for file_name in os.listdir(directory_path) if file_name.endswith(".session")]

    matching_json_files = []

    for session_file in sorted(session_files):
        base_name = os.path.splitext(session_file)[0]
        json_file_name = f"{base_name}.json"

        if json_file_name in os.listdir(directory_path) and base_name != excluded_phone:
            matching_json_files.append((session_file, json_file_name))

    return matching_json_files


def set_admin(new_admin_username, rank, group_name, client):
    user_entity = client.get_entity(new_admin_username)

    client(functions.channels.EditAdminRequest(
        channel=group_name,
        user_id=user_entity.id,
        admin_rights=types.ChatAdminRights(
            change_info=True,
            post_messages=True,
            edit_messages=True,
            delete_messages=True,
            ban_users=True,
            invite_users=True,
            pin_messages=True,
            add_admins=True,
            anonymous=True,
            manage_call=True,
            other=True,
            manage_topics=True,
            post_stories=True,
            edit_stories=True,
            delete_stories=True
        ),
        rank=rank
    ))

    log_message(f'{datetime.now()}: Добавил админа.')

def remove_admin(username, group_name, client):
    user_entity = client.get_entity(username)

    client(functions.channels.EditAdminRequest(
        channel=group_name,
        user_id=user_entity.id,
        admin_rights=types.ChatAdminRights(
            change_info=False,
            post_messages=False,
            edit_messages=False,
            delete_messages=False,
            ban_users=False,
            invite_users=False,
            pin_messages=False,
            add_admins=False,
            anonymous=False,
            manage_call=False,
            other=False,
            manage_topics=False,
            post_stories=False,
            edit_stories=False,
            delete_stories=False
        ),
        rank="simple"
    ))
        
    log_message(f'{datetime.now()}: Удалил админа.')

def transfer_owner_rights(username, group_name, two_fa, client):
    user_entity = client.get_entity(username)
    user_id = user_entity.id

    password_check = password.compute_check(client(functions.account.GetPasswordRequest()), two_fa)

    client(functions.channels.EditCreatorRequest(
                channel=group_name,
                user_id=user_id,
                password=password_check
    ))

    log_message(f'{datetime.now()}: Передал права владельца.')



def main(global_client, data):
    global processed_accounts
    client = global_client
    api_id, api_hash, two_fa, phone, owner_username, group_name = data
    twoFa = two_fa

    sessions_directory = SESSIONS_DIRECTORY

    owners_data = find_json_files(sessions_directory, phone)

    if not owners_data:
        log_message("Программа завершает работу. В директории нет пар файлов .session и .json.")
        sys.exit("Программа завершает работу. В директории нет пар файлов .session и .json.")

    owner_counter = 0
    current_owner_username = owner_username
    owner_session, owner_json = owners_data[owner_counter]
    full_path_to_json = os.path.join(sessions_directory, owner_json)

    with open(full_path_to_json, "r") as data:
        json_data = json.load(data)

    try:
        next_owner_two_fa = json_data["twoFA"]
        next_owner_api_id = json_data["app_id"]
        next_owner_api_hash = json_data["app_hash"]
        next_owner_username = json_data["username"]
        temp_owner_username = json_data["username"]
    except KeyError:
        log_message("Программа завершает работу. В файле не найдены нужные данные для owner.")
        sys.exit("Программа завершает работу. В файле не найдены нужные данные для owner.")

    try:
        set_admin(next_owner_username, "next-owner-admin", group_name, client)
        log_message(f'{datetime.now()}: Назначили админом следующего owner ({next_owner_username})', account_username=current_owner_username)
        time.sleep(5)
    except (errors.rpcerrorlist.FloodWaitError, errors.rpcerrorlist.FloodError, errors.rpcerrorlist.PeerFloodError):
        log_message(f'{datetime.now()}: Программа не может начать работу. Установлен лимит для первого owner ({current_owner_username})', account_username=current_owner_username)
        sys.exit(f'{datetime.now()}: Программа не может начать работу. Установлен лимит для первого owner ({current_owner_username})')

    usernames_path = USERNAMES_PATH
    with open(usernames_path, "r") as users_file:
        users = [line.strip() for line in users_file.readlines() if line.strip()]
        for user in users.copy():
            try:
                set_admin(user, "admin", group_name, client)
                time.sleep(5)

                remove_admin(user, group_name, client)
                time.sleep(5)

                users.remove(user)
                with open(usernames_path, 'w', encoding='utf-8') as file:
                    file.write('\n'.join(users))

                log_message(f'{datetime.now()}: Добавлен и удален администратор: {user}', account_username=current_owner_username, added_username=user)
                
            except (errors.rpcerrorlist.FloodWaitError, errors.rpcerrorlist.FloodError, errors.rpcerrorlist.PeerFloodError):
                log_message(f'{datetime.now()}: Лимит для owner ({current_owner_username})', account_username=current_owner_username)

                if len(owners_data) > owner_counter + 1:
                    owner_session = owners_data[owner_counter][0]
                    owner_json = owners_data[owner_counter][1]

                    full_path_to_owner_json = os.path.join(sessions_directory, owner_json)
                    full_path_to_owner_session = os.path.join(sessions_directory, owner_session)

                    with open(full_path_to_owner_json, "r") as data:
                        json_data = json.load(data)

                    try:
                        next_owner_two_fa = json_data["twoFA"]
                        next_owner_api_id = json_data["app_id"]
                        next_owner_api_hash = json_data["app_hash"]
                        next_owner_username = json_data["username"]
                    except KeyError:
                        log_message("Программа завершает работу. В файле не найдены нужные данные для owner.")
                        sys.exit("Программа завершает работу. В файле не найдены нужные данные для owner.")

                    transfer_owner_rights(next_owner_username, group_name, twoFa, client)
                    log_message(f'{datetime.now()}: Передали права владельца.', account_username=current_owner_username)
                    time.sleep(5)
                    client.disconnect()
                    log_message(f'{datetime.now()}: Вышел из аккаунта owner ({current_owner_username})', account_username=current_owner_username)

                    twoFa = next_owner_two_fa

                    if temp_owner_username == next_owner_username:
                        current_owner_username = username
                    else:
                        current_owner_username = temp_owner_username
                        temp_owner_username = next_owner_username

                    client = auth(full_path_to_owner_session, [next_owner_api_id, next_owner_api_hash, twoFa])
                    log_message(f'{datetime.now()}: Зашел в аккаунта owner ({next_owner_username})', account_username=current_owner_username)

                    owner_counter += 1
                    owner_session = owners_data[owner_counter][0]
                    owner_json = owners_data[owner_counter][1]

                    full_path_to_owner_json = os.path.join(sessions_directory, owner_json)
                    full_path_to_owner_session = os.path.join(sessions_directory, owner_session)

                    with open(full_path_to_owner_json, "r") as data:
                        json_data = json.load(data)

                    try:
                        next_owner_username = json_data["username"]
                    except KeyError:
                        log_message("Программа завершает работу. В файле не найдены нужные данные для owner.")
                        sys.exit("Программа завершает работу. В файле не найдены нужные данные для owner.")

                    remove_admin(current_owner_username, group_name, client)
                    log_message(f'{datetime.now()}: Сняли права админа с старого owner ({current_owner_username})', account_username=current_owner_username)

                    time.sleep(5)
                    set_admin(next_owner_username, "next-owner-admin", group_name, client)
                    log_message(f'{datetime.now()}: Назначили админом следующего owner ({next_owner_username})', account_username=current_owner_username)

                    time.sleep(5)
                    continue

                else:   
                    log_message("Программа завершает работу. Больше нет аккаунтов для owner", account_username=current_owner_username)
                    sys.exit("Программа завершает работу. Больше нет аккаунтов для owner")

            except ValueError:
                log_message(f'{datetime.now()}: Пользователь ({user}) не найден. Пропускаем.', account_username=current_owner_username)
                users.remove(user)
                skipped_usernames += 1
                continue

    processed_accounts += 1


if __name__ == "__main__":
    start_time = datetime.now()
    log_message(f'{start_time}: Начал работу')
    
    phone = input("Введите номер телефона основного аккаунта: ")

    directory_path = SESSIONS_DIRECTORY

    files_to_check = [f'{phone}.session', f'{phone}.json']

    if check_files_exist(directory_path, files_to_check):
        log_message("Оба файла существуют.")
        full_path_to_json = os.path.join(directory_path, f'{phone}.json')

        with open(full_path_to_json, "r") as data:
            json_data = json.load(data)

        try:
            two_fa = json_data["twoFA"]
            api_id = json_data["app_id"]
            api_hash = json_data["app_hash"]
            username = json_data["username"]
        except KeyError:
            log_message("Программа завершает работу. В файле не найдены нужные данные.")
            sys.exit("Программа завершает работу. В файле не найдены нужные данные.")

        full_path_to_session = os.path.join(directory_path, f'{phone}.session')
        try:
            global_client = auth(full_path_to_session, [api_id, api_hash, two_fa])
        except errors.rpcbaseerrors.BadRequestError:
            log_message("Программа завершает работу. Некорректные сессии.")
            sys.exit("Программа завершает работу. Некорректные сессии.")

        try:
            group_name = input("Введите группу, в формате ссылки или собаки: ")
            group_entity = global_client.get_entity(group_name)
        except errors.rpcerrorlist.UsernameInvalidError:
            log_message("Программа завершает работу из-за отсутствия группы.")
            sys.exit("Программа завершает работу из-за отсутствия группы.")

        try:
            if group_entity.creator:
                main(global_client, [api_id, api_hash, two_fa, phone, username, group_name])

                log_statistics()
            else:
                log_message("Программа завершает работу. Вы не владелец.")
                sys.exit("Программа завершает работу. Вы не владелец.")
        except KeyError as e:
            log_message(f"Программа завершает работу. Ошибка: {e}")
            sys.exit("Программа завершает работу. Ошибка в данных.")
    else:
        log_message("Программа завершает работу из-за отсутствия файла.")
        sys.exit("Программа завершает работу из-за отсутствия файла.")
