import os
import io
import fnmatch
import re
import base64

import local_settings

from trello import TrelloClient


def init_board(client, board_name='Tiddly'):
    try:
        tiddly_board = None
        tiddly_board = next(board for board in client.list_boards() if board.name == 'Tiddly')
    except StopIteration:
        tiddly_board = client.add_board('Tiddly')
    for label in tiddly_board.get_labels():
        tiddly_board.client.fetch_json('/labels/' + label.id, http_method='DELETE')
    return tiddly_board

def init_import_list(board, list_name='Imported'):
    try:
        t_list = None
        t_list = next(x for x in board.all_lists() if x.name == 'Imported')
        t_list.archive_all_cards()
        for card in t_list.list_cards(card_filter='closed'):
            card.delete()
    except StopIteration:
        t_list = board.add_list(name=list_name)
    return t_list

def handle_tiddler(tiddler):
    """Meta files:
            Title is filename, type is type
            May have to rename image file
    """

def read_tiddler(file_name):
    f = open(file_name, encoding='utf-8')
    in_header = True
    t_dict = dict()
    body = []
    for line in f.readlines():
        if line == '\n':
            in_header = False
            continue
        if in_header:
            match = re.search(r"(.*?): (.*)", line)
            t_dict[match.group(1)] = match.group(2)
        else:
            body.append(line)
    f.close()
    t_dict['*body*'] = body
    return t_dict

def tags_to_labels(t_dict, t_board):
    board_labels = t_board.get_labels()
    card_labels = []
    if 'tags' in t_dict:
        for tag in t_dict['tags'].split(' '):
            try:
                label = next(x for x in board_labels if x.name == tag)
            except StopIteration:
                label = t_board.add_label(tag, 'blue')
            card_labels.append(label)
    return card_labels

def convert_tid(t_list, file_name):
    t_dict = read_tiddler(file_name)
    card_labels = tags_to_labels(t_dict, t_list.board)
    if 'title' in t_dict:
        card_name = t_dict['title']
    else:
        card_name = 'No card name'
    # Some tiddlers have embedded data encoded as base64.
    embedded_mime_types = ['image/gif']
    if 'type' in t_dict and t_dict['type'] in embedded_mime_types:
        mime_type = t_dict['type']
        decoded = base64.b64decode(''.join(t_dict['*body*']))
        decoded_file = io.BytesIO(decoded)
        card = t_list.add_card(card_name, labels=card_labels)
        card.attach(card_name, mimeType=mime_type, file=decoded_file)
    else:
        desc = "\n".join(t_dict['*body*'])
        if len(desc) <= 16384:
            card = t_list.add_card(card_name, desc="\n".join(t_dict['*body*']), labels=card_labels)
        else:
            print('Body too long for "%s"' % (card_name))


def convert_meta(t_list, file_name):
    t_dict = read_tiddler(file_name)
    card_labels = tags_to_labels(t_dict, t_list.board)
    base_name = t_dict['title'].replace(' ', '_')
    dir_name = os.path.dirname(file_name)
    f_name = os.path.join(dir_name, base_name)
    f = open(f_name, 'rb')
    mime_type = t_dict['type']
    card_name = base_name
    card = t_list.add_card(card_name, labels=card_labels)
    card.attach(card_name, mimeType=mime_type, file=f)

def convert_tiddlers(t_list, tiddler_dir='./test_tiddlers/'):
    for file in os.listdir(tiddler_dir):
        if fnmatch.fnmatch(file, '*.tid'):
            convert_tid(t_list, os.path.abspath(tiddler_dir + file))
        elif fnmatch.fnmatch(file, '*.meta'):
            convert_meta(t_list, os.path.abspath(tiddler_dir + file))

def main():
    client = TrelloClient(api_key=local_settings.API_KEY,
                         api_secret=local_settings.API_SECRET,
                         token=local_settings.TOKEN,
                         token_secret=local_settings.TOKEN_SECRET)

    board = init_board(client)
    t_list = init_import_list(board)
    #convert_tiddlers(t_list)
    convert_tiddlers(t_list, './tiddlers/')

if __name__ == '__main__':
    main()
    print("Done")
