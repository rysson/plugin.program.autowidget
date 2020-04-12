import xbmc
import xbmcaddon
import xbmcgui

import json
import os
import re

try:
    from urllib.parse import parse_qsl
except ImportError:
    from urlparse import parse_qsl

from resources.lib.common import utils

_addon = xbmcaddon.Addon()
_addon_path = xbmc.translatePath(_addon.getAddonInfo('profile'))
_addon_version = _addon.getAddonInfo('version')
_home = xbmc.translatePath('special://home/')
if xbmc.getCondVisibility('System.HasAddon(script.skinshortcuts)'):
    _shortcuts = xbmcaddon.Addon('script.skinshortcuts')
    _shortcuts_path = xbmc.translatePath(_shortcuts.getAddonInfo('profile'))
else:
    _shortcuts_path = ''

folder_add = utils.get_art('folder-add.png')
folder_shortcut = utils.get_art('folder-shortcut.png')
folder_sync = utils.get_art('folder-sync.png')
share = utils.get_art('share.png')
folder_settings = utils.get_art('folder-settings.png')
folder_clone = utils.get_art('folder-clone.png')
folder_explode = utils.get_art('folder-explode.png')


def write_path(group_def, path_def=None, update=''):
    filename = os.path.join(_addon_path, '{}.group'.format(group_def['id']))

    if path_def:
        if update:
            for path in group_def['paths']:
                if path['id'] == update:
                    group_def['paths'][group_def['paths'].index(path)] = path_def
        else:
            group_def['paths'].append(path_def)

    utils.write_json(filename, group_def)


def get_group_by_id(group_id):
    if not group_id:
        return
    
    filename = '{}.group'.format(group_id)
    path = os.path.join(_addon_path, filename)
    
    try:
        group_def = utils.read_json(path)
    except ValueError:
        utils.log('Unable to parse: {}'.format(path))
    
    return group_def


def get_path_by_id(path_id, group_id=None):
    if not path_id:
        return
        
    for defined in find_defined_paths(group_id):
        if defined.get('id', '') == path_id:
            return defined
            
            
def get_widget_by_id(widget_id, group_id=None):
    if not widget_id:
        return
        
    for defined in find_defined_widgets(group_id):
        if defined.get('id', '') == widget_id:
            return defined
    
    
def find_defined_groups(_type=''):
    groups = []
    
    for filename in [x for x in os.listdir(_addon_path) if x.endswith('.group')]:
        path = os.path.join(_addon_path, filename)
        
        try:
            group_def = utils.read_json(path)
        except ValueError:
            utils.log('Unable to parse: {}'.format(path))
        
        if _type:
            if group_def['type'] == _type:
                groups.append(group_def)
        else:
            groups.append(group_def)

    return groups
    
    
def find_defined_paths(group_id=None):
    paths = []
    if group_id:
        filename = '{}.group'.format(group_id)
        path = os.path.join(_addon_path, filename)
        
        try:
            group_def = utils.read_json(path)
        except ValueError:
            utils.log('Unable to parse: {}'.format(path))
        
        return group_def['paths']
    else:
        for group in find_defined_groups():
            paths.append(find_defined_paths(group_id=group.get('id')))
    
    return paths
    

def find_defined_widgets(group_id=None):
    addon_files = os.listdir(_addon_path)
    widgets = []
    
    widget_files = [x for x in addon_files if x.endswith('.widget')]
    for widget_file in widget_files:
        widget_def = utils.read_json(os.path.join(_addon_path, widget_file))
    
        if widget_def:
            if not group_id:
                widgets.append(widget_def)
            elif group_id == widget_def['group']:
                widgets.append(widget_def)
    
    return widgets
    
    
def add_from_context(labels):
    _type = _add_as(labels['path'], labels['is_folder'])
    if _type not in ['clone', 'explode']:
        labels['target'] = _type
        group_def = _group_dialog(_type)
        if group_def:
            _add_path(group_def, labels)
            if _type == 'shortcut':
                xbmc.executebuiltin('UpdateLibrary(video)')
    elif _type == 'clone':
        labels['target'] = 'shortcut'
        _copy_path(labels)
    elif _type == 'explode':
        labels['target'] = 'widget'
        _copy_path(labels)
            
            
def _add_as(path, is_folder):
    types = [_addon.getLocalizedString(32051), _addon.getLocalizedString(32052),
             'Clone', 'Explode', _addon.getLocalizedString(32053)]
    art = [folder_shortcut, folder_sync, folder_clone, folder_explode, folder_settings]
    
    if is_folder:
        types = types[:4]
    else:
        if any(i in path for i in ['addons://user', 'plugin://']) and not parse_qsl(path):
            pass
        else:
            types = [types[0]]

    options = []
    for idx, type in enumerate(types):
        li = xbmcgui.ListItem(type)
        
        li.setArt(art[idx])
        options.append(li)
    
    dialog = xbmcgui.Dialog()
    idx = dialog.select('Add as...', options, useDetails=True)
    if idx < 0:
        return ''
    
    return types[idx].lower()
            
            
def _group_dialog(_type, group_id=None):
    _type = 'shortcut' if _type == 'settings' else _type
    groups = find_defined_groups(_type)
    names = [group['label'] for group in groups]
    ids = [group['id'] for group in groups]
    
    index = -1
    options = []
    offset = 1
    
    if _type == 'widget':
        new_widget = xbmcgui.ListItem(_addon.getLocalizedString(32015))
        new_widget.setArt(folder_add)
        options.append(new_widget)
    else:
        new_shortcut = xbmcgui.ListItem(_addon.getLocalizedString(32017))
        new_shortcut.setArt(share)
        options.append(new_shortcut)
        
    if group_id:
        index = ids.index(group_id) + 1
    
    for group in groups:
        item = xbmcgui.ListItem(group['label'])
        item.setArt(folder_sync if group['type'] == 'widget' else folder_shortcut)
        options.append(item)
    
    dialog = xbmcgui.Dialog()
    choice = dialog.select(_addon.getLocalizedString(32054), options, preselect=index,
                           useDetails=True)
    
    if choice < 0:
        dialog.notification('AutoWidget', _addon.getLocalizedString(32034))
    elif (choice, _type) == (0, 'widget'):
        return _group_dialog(_type, add_group('widget'))
    elif choice == 0:
        return _group_dialog(_type, add_group('shortcut'))
    else:
        return groups[choice - offset]


def add_group(target):
    dialog = xbmcgui.Dialog()
    group_name = dialog.input(heading=_addon.getLocalizedString(32037))
    group_id = ''
    
    if group_name:
        group_id = utils.get_unique_id(group_name)
        filename = os.path.join(_addon_path, '{}.group'.format(group_id))
        group_def = {'label': group_name,
                     'type': target,
                     'paths': [],
                     'id': group_id,
                     'info': {'plot': ''},
                     'art': folder_sync if target == 'widget' else folder_shortcut,
                     'version': _addon_version}
    
        utils.write_json(filename, group_def)
            
        xbmc.executebuiltin('Container.Refresh()')
    else:
        dialog.notification('AutoWidget', _addon.getLocalizedString(32038))
    
    return group_id
    
    
def _add_path(group_def, labels, over=False):
    if not over:
        if group_def['type'] == 'shortcut':
            heading = _addon.getLocalizedString(32043)
        elif group_def['type'] == 'widget':
            heading = _addon.getLocalizedString(32044)
        
        labels['label'] = xbmcgui.Dialog().input(heading=heading,
                                                 defaultt=labels['label'])
                                                 
    labels['id'] = utils.get_unique_id(labels['label'])
    labels['version'] = _addon_version
    
    write_path(group_def, path_def=labels)


def clean():
    dialog = xbmcgui.Dialog()
    choice = dialog.yesno('AutoWidget', _addon.getLocalizedString(32067))

    if not choice:
        return

    to_remove = []
    
    widgets = find_defined_widgets()
    groups = find_defined_groups()
    if _shortcuts_path:
        shortcuts = os.listdir(_shortcuts_path)
        
    for widget_def in widgets:
        remove = True
        widget_id = widget_def['id']
        widget_group = widget_def['group']
        
        for group_def in groups:
            group_id = group_def['id']
            
            if group_id == widget_group:
                remove = False
        
        if shortcuts:
            for shortcut in shortcuts:
                shortcut_file = os.path.join(_shortcuts_path, shortcut)
                shortcut_def = utils.read_file(shortcut_file)
                
                if shortcut_def:
                    if widget_id in shortcut_def:
                        remove = False

        if remove:
            to_remove.append(widget_id)
            
    for remove in to_remove:
        filename = '{}.widget'.format(remove)
        utils.remove_file(os.path.join(_addon_path, filename))


def _copy_path(path_def):
    _windows = {'programs':     ['program', 'script'],
                'addonbrowser': ['addon',   'addons'],
                'music':        ['audio',   'music'],
                'pictures':     ['image',   'picture'],
                'videos':       ['video',   'videos']}
    
    params = {'jsonrpc': '2.0', 'method': 'Files.GetDirectory',
              'params': {'directory': path_def['path'],
                         'properties': ['title', 'art', 'plot']},
              'id': 1}
    group_id = add_group(path_def['target'])
    group_def = get_group_by_id(group_id)
    files = xbmc.executeJSONRPC(json.dumps(params))
    if 'error' not in files:
        files = json.loads(files)['result']['files']
        for file in files:
            if file['type'] in ['movie', 'episode', 'musicvideo', 'song']:
                continue
            
            labels = {'label': file['label'],
                      'is_folder': file['filetype'] == 'directory',
                      'content': ''}
            
            path = file['file']
            if path != 'addons://user/':
                path = path.replace('addons://user/', 'plugin://')
            labels['path'] = path
            
            labels['art'] = {i: file['art'][i] if i in file['art'] else ''
                         for i in ['poster', 'fanart', 'banner', 'landscape',
                                   'clearlogo', 'clearart', 'icon', 'thumb']}
            for label in labels['art']:
                labels['art'][label] = labels['art'][label].replace(_home,
                                                            'special://home/')
            
            if 'plot' in file:
                labels['info'] = {'plot': file['plot']}
            labels['target'] = path_def['target']
            
            for _key in _windows:
                if any(i in path for i in _windows[_key]):
                    labels['window'] = _key
                    
            _add_path(group_def, labels, over=True)
