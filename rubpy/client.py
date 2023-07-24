import os
#import io
import aiofiles
import asyncio
#import asyncio
import logging
from .crypto import Crypto
from .structs import Struct
from Crypto.PublicKey import RSA
from . import __name__ as logger_name
from .network import Connection, Proxies
from .gadgets import exceptions, methods, thumbnail
from .sessions import StringSession, SQLiteSession


class Client:
    configuire = {
        'package': 'web.rubika.ir',
        'platform': 'Web',
        'app_name': 'Main',
        'user_agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko)'
                       'Chrome/102.0.0.0 Safari/537.36'),
        'api_version': '6',
        'app_version': '4.3.3'
    }

    def __init__(self,
        session,
        proxy=None,
        logger=None,
        timeout=20,
        lang_code='fa',
        user_agent=None,
        request_retries=5, *args, **kwargs):

        """Client
            Args:
                session_name (`str` | `rubpy.sessions.StringSession`):
                    The file name of the session file that is used
                    if there is a string Given (may be a complete path)
                    or it could be a string session
                    [rubpy.sessions.StringSession]

                proxy (` rubpy.network.Proxies `, optional): To set up a proxy

                user_agent (`str`, optional):
                    Client uses the web version, You can set the usr-user_agent

                timeout (`int` | `float`, optional):
                    To set the timeout `` default( `20 seconds` )``

                logger (`logging.Logger`, optional):
                    Logger base for use.

                lang_code(`str`, optional):
                    To set the lang_code `` default( `fa` ) ``
        """

        if isinstance(session, str):
            session = SQLiteSession(session)

        elif not isinstance(session, StringSession):
            raise TypeError('The given session must be a '
                            'str or [rubpy.sessions.StringSession]')

        if not isinstance(logger, logging.Logger):
            logger = logging.getLogger(logger_name)

        if proxy and not isinstance(proxy, Proxies):
            raise TypeError(
                'The given proxy must be a [rubpy.network.Proxies]')

        self._dcs = None
        self._key = None
        self._auth = None
        self._guid = None
        self._proxy = proxy
        self._logger = logger
        self._timeout = timeout
        self._session = session
        self._handlers = {}
        self._request_retries = request_retries
        self._user_agent = user_agent or self.configuire['user_agent']
        self._platform = {
            'package': kwargs.get('package', self.configuire['package']),
            'platform': kwargs.get('platform', self.configuire['platform']),
            'app_name': kwargs.get('app_name', self.configuire['app_name']),
            'app_version': kwargs.get('app_version',
                                      self.configuire['app_version']),
            'lang_code': lang_code}

    async def __call__(self, request: object):
        try:
            result = await self._connection.execute(request)

            # update session
            if result.__name__ == 'signIn' and result.status == 'OK':
                result.auth = Crypto.decrypt_RSA_OAEP(self._private_key, result.auth)
                self._key = Crypto.passphrase(result.auth)
                self._auth = result.auth
                self._session.insert(
                    auth=self._auth,
                    guid=result.user.user_guid,
                    user_agent=self._user_agent,
                    phone_number=result.user.phone,
                    private_key=self._private_key)

                await self(
                    methods.authorisations.RegisterDevice(
                        self._user_agent,
                        lang_code=self._platform['lang_code'],
                        app_version=self._platform['app_version'])
                )

            return result

        except AttributeError:
            raise exceptions.NoConnection(
                'You must first connect the Client'
                ' with the *.connect() method')

    async def __aenter__(self):
        return await self.start(phone_number=None)

    async def __aexit__(self, *args, **kwargs):
        return await self.disconnect()

    async def start(self, phone_number: str, *args, **kwargs):
        if not hasattr(self, '_connection'):
            await self.connect()

        try:
            self._logger.info('user info', extra={'data': await self.get_me()})

        except (exceptions.NotRegistrred, exceptions.InvalidInput):
            self._logger.debug('user not registered!')
            if phone_number is None:
                phone_number = input('Phone Number: ')
                is_phone_number_true = True
                while is_phone_number_true:
                    if input(f'Is the {phone_number} correct[y or n] > ').lower() == 'y':
                        is_phone_number_true = False
                    else:
                        phone_number = input('Phone Number: ')

            if phone_number.startswith('0'):
                phone_number = '98{}'.format(phone_number[1:])
            elif phone_number.startswith('+98'):
                phone_number = phone_number[1:]
            elif phone_number.startswith('0098'):
                phone_number = phone_number[2:]

            result = await self(
                methods.authorisations.SendCode(
                    phone_number=phone_number, *args, **kwargs))

            if result.status == 'SendPassKey':
                while True:
                    pass_key = input(f'Password [{result.hint_pass_key}] > ')
                    result = await self(
                        methods.authorisations.SendCode(
                            phone_number=phone_number,
                            pass_key=pass_key, *args, **kwargs))

                    if result.status == 'OK':
                        break

            public_key, self._private_key = Crypto.create_keys()
            while True:
                phone_code = input('Code: ')
                result = await self(
                    methods.authorisations.SignIn(
                        phone_code=phone_code,
                        phone_number=phone_number,
                        phone_code_hash=result.phone_code_hash,
                        public_key=public_key,
                        *args, **kwargs))

                if result.status == 'OK':
                    break

        return self

    async def connect(self):
        self._connection = Connection(client=self)
        information = self._session.information()
        self._logger.info(f'the session information was read {information}')
        if information:
            self._auth = information[1]
            self._guid = information[2]
            self._private_key = information[4]
            if isinstance(information[3], str):
                self._user_agent = information[3]

        return self

    async def disconnect(self):
        try:
            await self._connection.close()
            self._logger.info(f'the client was disconnected')

        except AttributeError:
            raise exceptions.NoConnection(
                'You must first connect the Client'
                ' with the *.connect() method')

    async def run_until_disconnected(self):
        return await self._connection.receive_updates()

    # handler methods

    def on(self, handler):
        def MetaHandler(func):
            self.add_handler(func, handler)
            return func
        return MetaHandler

    def add_handler(self, func, handler):
        self._handlers[func] = handler

    def remove_handler(self, func):
        try:
            self._handlers.pop(func)
        except KeyError:
            pass

    # async methods

    async def get_me(self, *args, **kwargs):
        return await self(methods.users.GetUserInfo(self._guid))

    async def upload(self, file, *args, **kwargs):
        return await self._connection.upload_file(file=file, *args, **kwargs)

    async def download_file_inline(self, file_inline, file: str = None, *args, **kwargs):
        result = await self._connection.download(
            file_inline.dc_id,
            file_inline.file_id,
            file_inline.access_hash_rec)

        if isinstance(file, str):
            with open(file, 'wb+') as _file:
                _file.write(result)
                return file

        return result

# ---------------- Users Methods ----------------

    async def get_user_info(self, user_guid: str):
        return await self(methods.users.GetUserInfo(user_guid))

    async def block_user(self, user_guid: str):
        return await self(methods.users.SetBlockUser(user_guid, 'Block'))

    async def unblock_user(self, user_guid: str):
        return await self(methods.users.SetBlockUser(user_guid, 'Unblock'))

    async def delete_user_chat(self, user_guid: str, last_deleted_message_id: str):
        return await self(methods.users.DeleteUserChat(user_guid, last_deleted_message_id))

    async def check_user_username(self, username: str):
        return await self(methods.users.CheckUserUsername(username.replace('@', '')))

# ---------------- Chats Methods ----------------

    async def upload_avatar(self, object_guid: str, main_file_id: str, thumbnail_file_id: str):
        return await self(methods.chats.UploadAvatar(object_guid, main_file_id, thumbnail_file_id))

    async def delete_avatar(self, object_guid: str, avatar_id: str):
        return await self(methods.chats.DeleteAvatar(object_guid, avatar_id))

    async def get_avatars(self, object_guid: str):
        return await self(methods.chats.GetAvatars(object_guid))

    async def get_chats(self, start_id: int = None):
        return await self(methods.chats.GetChats(start_id))

    async def seen_chats(self, seen_list: dict):
        return await self(methods.chats.SeenChats(seen_list))

    async def get_chat_ads(self, state: int):
        return await self(methods.chats.GetChatAds(state))

    async def set_action_chat(self, object_guid: str, action: str):
        '''
        alloweds: ["Mute", "Unmute"]
        result = await client.set_action_chat('object_guid', 'Mute')
        print(result)
        '''
        return await self(methods.chats.SetActionChat(object_guid, action))

    async def get_chats_updates(self, state: int = None):
        return await self(methods.chats.GetChatsUpdates(state))

    async def send_chat_activity(self, object_guid: str, activity: str = None):
        return await self(methods.chats.SendChatActivity(object_guid, activity))

    async def delete_chat_history(self, object_guid: str):
        return await self(methods.chats.DeleteChatHistory(object_guid))

    async def search_chat_messages(self, object_guid: str, search_text: str, type: str = 'Hashtag'):
        return await self(methods.chats.SearchChatMessages(object_guid, search_text, type))

# ---------------- Extras Methods ----------------

    async def search_global_objects(self, search_text: str):
        return await self(methods.extras.SearchGlobalObjects(search_text))

    async def get_abs_objects(self, objects_guids: list):
        return await self(methods.extras.GetAbsObjects(objects_guids))

    async def get_object_by_username(self, username: str):
        return await self(methods.extras.GetObjectByUsername(username.replace('@', '')))

    async def get_link_from_app_url(self, app_url: str):
        return await self(methods.extras.GetLinkFromAppUrl(app_url))

    async def create_voice_call(self, object_guid: str):
        if object_guid.startswith('c'):
            return await self(methods.channels.CreateChannelVoiceChat(object_guid))
        elif object_guid.startswith('g'):
            return await self(methods.groups.CreateGroupVoiceChat(object_guid))
        else:
            print('Invalid Object Guid')
            return False

    async def set_voice_chat_setting(self, object_guid: str, voice_chat_id: str, title: str = None):
        if object_guid.startswith('c'):
            return await self(methods.channels.SetChannelVoiceChatSetting(object_guid, voice_chat_id, title, ['title']))
        elif object_guid.startswith('g'):
            return await self(methods.groups.SetGroupVoiceChatSetting(object_guid, voice_chat_id, title, ['title']))
        else:
            print('Invalid Object Guid')
            return False

# ---------------- Groups Methods ----------------

    async def add_group(self, title: str, member_guids: list):
        return await self(methods.groups.AddGroup(title, member_guids))

    async def join_group(self, link: str):
        return await self(methods.groups.JoinGroup(link))

    async def leave_group(self, group_guid: str):
        return await self(methods.groups.LeaveGroup(group_guid))

    async def remove_group(self, group_guid: str):
        return await self(methods.groups.RemoveGroup(group_guid))

    async def get_group_info(self, group_guid: str):
        return await self(methods.groups.GetGroupInfo(group_guid))

    async def get_group_link(self, group_guid: str):
        return await self(methods.groups.GetGroupLink(group_guid))

    async def set_group_link(self, group_guid: str):
        return await self(methods.groups.SetGroupLink(group_guid))

    async def edit_group_info(self,
         group_guid: str,
         title: str = None,
         description: str = None,
         chat_history_for_new_members: str = None,
     ):
        updated_parameters = []

        if title:
            updated_parameters.append('title')
        if description:
            updated_parameters.append('description')
        if chat_history_for_new_members:
            updated_parameters.append('chat_history_for_new_members')

        return await self(methods.groups.EditGroupInfo(
            group_guid, updated_parameters, title, description, chat_history_for_new_members))

    async def set_group_admin(self,
        group_guid: str,
        member_guid: str,
        access_list: list,
        action: str = 'SetAdmin',
    ):
        return await self(methods.groups.SetGroupAdmin(group_guid, member_guid, access_list, action))

    async def ban_group_member(self, group_guid: str, member_guid: str):
        return await self(methods.groups.BanGroupMember(group_guid, member_guid, 'Set'))

    async def unban_group_member(self, group_guid: str, member_guid: str):
        return await self(methods.groups.BanGroupMember(group_guid, member_guid, 'Unset'))

    async def add_group_members(self, group_guid: str, member_guids: list):
        return await self(methods.groups.AddGroupMembers(group_guid, member_guids))

    async def get_group_all_members(self, group_guid: str, search_text: str = '', start_id: int = None):
        return await self(methods.groups.GetGroupAllMembers(group_guid, search_text, start_id))

    async def get_group_admin_members(self, group_guid: str, start_id: int = None):
        return await self(methods.groups.GetGroupAdminMembers(group_guid, start_id))

    async def get_group_mention_list(self, group_guid: str, search_mention: str = None):
        return await self(methods.groups.GetGroupMentionList(group_guid, search_mention))

    async def get_group_default_access(self, group_guid: str):
        return await self(methods.groups.GetGroupDefaultAccess(group_guid))

    async def set_group_default_access(self, group_guid: str, access_list: list):
        return await self(methods.groups.SetGroupDefaultAccess(group_guid, access_list))

    async def group_preview_by_join_link(self, group_link: str):
        return await self(methods.groups.GroupPreviewByJoinLink(group_link))

    async def delete_no_access_group_chat(self, group_guid: str):
        return await self(methods.groups.DeleteNoAccessGroupChat(group_guid))

    async def get_group_admin_access_list(self, group_guid: str, member_guid: str):
        return await self(methods.groups.GetGroupAdminAccessList(group_guid, member_guid))

    async def set_group_timer(self, group_guid: str, time: int):
        return await self(methods.groups.EditGroupInfo(group_guid, slow_mode=time, updated_parameters=['slow_mode']))

# ---------------- Messages Methods ----------------

    async def send_message(self,
        object_guid: str,
        message=None,
        reply_to_message_id: str = None,
        file_inline=None,
        type: str = methods.messages.File,
        thumb: bool = True, *args, **kwargs
    ):
        """_send message_

        Args:
            object_guid (str):
                _object guid_

            message (Any, optional):
                _message or cation or sticker_ . Defaults to None.

            reply_to_message_id (str, optional):
                _reply to message id_. Defaults to None.

            file_inline (typing.Union[pathlib.Path, bytes], optional):
                _file_. Defaults to None.

            type (str, optional):
                _file type_. Defaults to methods.messages.File.(
                    methods.messages.Gif,
                    methods.messages.Image,
                    methods.messages.Voice,
                    methods.messages.Music,
                    methods.messages.Video
                )

            thumb (bool, optional):
                if value is "True",
                    the lib will try to build the thumb ( require cv2 )
                if value is thumbnail.Thumbnail, to set custom
                Defaults to True.
        """

        if object_guid.lower() in ['me', 'self', 'cloud']:
            object_guid = self._guid

        if file_inline is not None:
            if not isinstance(file_inline, Struct):
                if isinstance(file_inline, str):
                    with open(file_inline, 'rb') as file:
                        kwargs['file_name'] = kwargs.get(
                            'file_name', os.path.basename(file_inline))
                        file_inline = file.read()

                if thumb is True:
                    if type == methods.messages.Image:
                        thumb = thumbnail.MakeThumbnail(file_inline)

                    elif type in [methods.messages.Gif, methods.messages.Video]:
                        thumb = thumbnail.MakeThumbnail.from_video(file_inline)

                    if thumb.image is None:
                        type = methods.messages.File
                        thumb = None

                # the problem will be fixed in the next version #debug
                # to avoid getting InputError
                # values are not checked in Rubika (optional)
                file_inline = await self.upload(file_inline, *args, **kwargs)
                file_inline['type'] = type
                file_inline['time'] = kwargs.get('time', 1)
                file_inline['width'] = kwargs.get('width', 200)
                file_inline['height'] = kwargs.get('height', 200)
                file_inline['music_performer'] = kwargs.get('performer', '')

                if isinstance(thumb, thumbnail.Thumbnail):
                    file_inline['time'] = thumb.seconds
                    file_inline['width'] = thumb.width
                    file_inline['height'] = thumb.height
                    file_inline['thumb_inline'] = thumb.to_base64()

        return await self(
            methods.messages.SendMessage(
                object_guid,
                message=message,
                file_inline=file_inline,
                reply_to_message_id=reply_to_message_id))

    async def send_photo(self,
        object_guid: str,
        photo: bytes,
        caption: str = None,
        file_name: str = None,
        width: int = None,
        height: int = None,
        thumb: str = None,
        reply_to_message_id: str = None,
        *args,
        **kwargs,
    ):
        if object_guid.lower() in ('me', 'self', 'cloud'):
            object_guid = self._guid

        if type(photo) != bytes:
            async with aiofiles.open(photo, 'rb') as file:
                file_name = os.path.basename(photo)
                kwargs['file_name'] = kwargs.get('file_name', file_name)
                photo = await file.read()
                await file.close()
        else:
            kwargs['file_name'] = kwargs.get('file_name', file_name)

        thumb = thumbnail.MakeThumbnail(photo)

        file_inline = await self.upload(photo, *args, **kwargs)
        file_inline['type'] = 'Image'

        if thumb and width and height != None:
            file_inline['width'] = width
            file_inline['height'] = height
            file_inline['thumb_inline'] = thumb
        else:
            if isinstance(thumb, thumbnail.Thumbnail):
                file_inline['width'] = thumb.width
                file_inline['height'] = thumb.height
                file_inline['thumb_inline'] = thumb.to_base64()

        return await self(
            methods.messages.SendMessage(
                object_guid,
                message=caption,
                file_inline=file_inline,
                reply_to_message_id=reply_to_message_id))

    async def send_file(self,
        object_guid: str,
        file: bytes,
        caption: str = None,
        file_name: str = None,
        reply_to_message_id: str = None,
        *args,
        **kwargs,
    ):
        if object_guid.lower() in ('me', 'self', 'cloud'):
            object_guid = self._guid

        if type(file) != bytes:
            async with aiofiles.open(file, 'rb') as ofile:
                file_name = os.path.basename(file)
                kwargs['file_name'] = kwargs.get('file_name', file_name)
                file = await ofile.read()
                await ofile.close()
        else:
            kwargs['file_name'] = kwargs.get('file_name', file_name)

        file_inline = await self.upload(file, *args, **kwargs)
        file_inline['type'] = 'File'

        return await self(
            methods.messages.SendMessage(
                object_guid,
                message=caption,
                file_inline=file_inline,
                reply_to_message_id=reply_to_message_id))

    async def send_gif(self,
        object_guid: str,
        gif: bytes,
        caption: str = None,
        file_name: str = None,
        thumb: str = None,
        time: str = None,
        width: int = None,
        height: int = None,
        reply_to_message_id: str = None,
        *args,
        **kwargs,
    ):
        if object_guid.lower() in ('me', 'self', 'cloud'):
            object_guid = self._guid

        if type(gif) != bytes:
            async with aiofiles.open(gif, 'rb') as file:
                file_name = os.path.basename(gif)
                kwargs['file_name'] = kwargs.get('file_name', file_name)
                file = await file.read()
                await file.close()
        else:
            kwargs['file_name'] = kwargs.get('file_name', file_name)

        file_inline = await self.upload(gif, *args, **kwargs)
        file_inline['type'] = 'Gif'

        thumb = thumbnail.MakeThumbnail.from_video(gif)

        if thumb and width and height and time != None:
            file_inline['width'] = width
            file_inline['height'] = height
            file_inline['thumb_inline'] = thumb
            file_inline['time'] = time
        else:
            if isinstance(thumb, thumbnail.Thumbnail):
                file_inline['time'] = thumb.seconds
                file_inline['width'] = thumb.width
                file_inline['height'] = thumb.height
                file_inline['thumb_inline'] = thumb.to_base64()

        return await self(
            methods.messages.SendMessage(
                object_guid,
                message=caption,
                file_inline=file_inline,
                reply_to_message_id=reply_to_message_id))

    async def send_video(self,
        object_guid: str,
        video: bytes,
        caption: str = None,
        file_name: str = None,
        thumb: str = None,
        time: str = None,
        width: int = None,
        height: int = None,
        reply_to_message_id: str = None,
        *args,
        **kwargs,
    ):
        if object_guid.lower() in ('me', 'self', 'cloud'):
            object_guid = self._guid

        if type(video) != bytes:
            async with aiofiles.open(video, 'rb') as file:
                file_name = os.path.basename(video)
                kwargs['file_name'] = kwargs.get('file_name', file_name)
                video = await file.read()
                await file.close()
        else:
            kwargs['file_name'] = kwargs.get('file_name', file_name)

        file_inline = await self.upload(video, *args, **kwargs)
        file_inline['type'] = 'Video'

        thumb = thumbnail.MakeThumbnail.from_video(video)

        if thumb and width and height and time != None:
            file_inline['width'] = width
            file_inline['height'] = height
            file_inline['thumb_inline'] = thumb
            file_inline['time'] = time
        else:
            if isinstance(thumb, thumbnail.Thumbnail):
                file_inline['time'] = thumb.seconds
                file_inline['width'] = thumb.width
                file_inline['height'] = thumb.height
                file_inline['thumb_inline'] = thumb.to_base64()

        return await self(
            methods.messages.SendMessage(
                object_guid,
                message=caption,
                file_inline=file_inline,
                reply_to_message_id=reply_to_message_id))

    async def send_music(self,
        object_guid: str,
        music: bytes,
        caption: str = None,
        file_name: str = None,
        time: str = None,
        music_performer: str = None,
        reply_to_message_id: str = None,
        *args,
        **kwargs,
    ):
        if object_guid.lower() in ('me', 'self', 'cloud'):
            object_guid = self._guid

        if type(music) != bytes:
            async with aiofiles.open(music, 'rb') as music_file:
                file_name = os.path.basename(music)
                kwargs['file_name'] = kwargs.get('file_name', file_name)
                music = await music_file.read()

        else:
            kwargs['file_name'] = kwargs.get('file_name', file_name)

        file_inline = await self.upload(music, *args, **kwargs)
        file_inline['type'] = 'Music'
        file_inline['auto_play'] = False
        file_inline['music_performer'] = kwargs.get('performer', music_performer or '')

        if time != None:
            file_inline['time'] = time
        else:
            file_inline['time'] = '60'

        return await self(
            methods.messages.SendMessage(
                object_guid,
                message=caption,
                file_inline=file_inline,
                reply_to_message_id=reply_to_message_id))

    async def send_voice(self,
        object_guid: str,
        music: bytes,
        caption: str = None,
        file_name: str = None,
        time: str = None,
        reply_to_message_id: str = None,
        *args,
        **kwargs,
    ):
        if object_guid.lower() in ('me', 'self', 'cloud'):
            object_guid = self._guid

        if type(music) != bytes:
            async with aiofiles.open(music, 'rb') as file:
                file_name = os.path.basename(music)
                kwargs['file_name'] = kwargs.get('file_name', file_name)
                music = await file.read()
        else:
            kwargs['file_name'] = kwargs.get('file_name', file_name)


        file_inline = await self.upload(music, *args, **kwargs)
        file_inline['type'] = 'Voice'
        file_inline['mime'] = 'ogg'
        file_inline['auto_play'] = False

        if time != None:
            file_inline['time'] = time
        else:
            file_inline['time'] = '60'

        return await self(
            methods.messages.SendMessage(
                object_guid,
                message=caption,
                file_inline=file_inline,
                reply_to_message_id=reply_to_message_id))

    async def edit_message(self, object_guid: str, message_id: str, text: str):
        return await self(methods.messages.EditMessage(object_guid, message_id, text))

    async def delete_messages(self, object_guid: str, message_ids: list, type: str = 'Global'):
        return await self(methods.messages.DeleteMessages(object_guid, message_ids, type))

    async def request_send_file(self, file_name: str, size: int, mime: str):
        return await self(methods.messages.RequestSendFile(file_name, size, mime))

    async def forward_messages(self, from_object_guid: str, to_object_guid: str, message_ids: list):
        return await self(methods.messages.ForwardMessages(from_object_guid, to_object_guid, message_ids))

    async def create_poll(self,
            object_guid: str,
            question: str,
            options: list,
            type: str = 'Regular',
            is_anonymous: bool = True,
            allows_multiple_answers: bool = False,
            correct_option_index: int = 0,
            explanation: str = None,
            reply_to_message_id: int = 0,
    ):
        if type == 'Regular':
            return await self(methods.messages.CreatePoll(
                object_guid=object_guid,
                question=question,
                options=options,
                allows_multiple_answers=allows_multiple_answers,
                is_anonymous=is_anonymous,
                reply_to_message_id=reply_to_message_id,
                type=type,
            ))
        else:
            return await self(methods.messages.CreatePoll(
                object_guid=object_guid,
                question=question,
                options=options,
                allows_multiple_answers=allows_multiple_answers,
                is_anonymous=is_anonymous,
                reply_to_message_id=reply_to_message_id,
                correct_option_index=correct_option_index,
                explanation=explanation,
                type=type,
            ))

    async def vote_poll(self, poll_id: str, selection_index: int):
        return await self(methods.messages.VotePoll(poll_id, selection_index))

    async def get_poll_status(self, poll_id: str):
        return await self(methods.messages.GetPollStatus(poll_id))

    async def get_poll_option_voters(self, poll_id: str, selection_index: int, start_id: int = None):
        return await self(methods.messages.GetPollOptionVoters(poll_id, selection_index, start_id))

    async def set_pin_message(self, object_guid: str, message_id: str, action: str = 'Pin'):
        return await self(methods.messages.SetPinMessage(object_guid, message_id, action))

    async def unset_pin_message(self, object_guid: str, message_id: str, action: str = 'Unpin'):
        return await self(methods.messages.SetPinMessage(object_guid, message_id, action))

    async def get_messages_updates(self, object_guid: str, state: int = None):
        return await self(methods.messages.GetMessagesUpdates(object_guid, state))

    async def search_global_messages(self, search_text: str, type: str = 'Text'):
        return await self(methods.messages.SearchGlobalMessages(search_text, type))

    async def click_message_url(self, object_guid: str, message_id: str, link_url: str):
        return await self(methods.messages.ClickMessageUrl(object_guid, message_id, link_url))

    async def get_messages_by_ID(self, object_guid: str, message_ids: list):
        return await self(methods.messages.GetMessagesByID(object_guid, message_ids))

    async def get_messages(self, object_guid: str, min_id: int, max_id: int, sort: str = 'FromMin', limit: int = 10):
        return await self(methods.messages.GetMessages(object_guid, min_id, max_id, sort, limit))

    async def get_messages_interval(self, object_guid: str, middle_message_id: str):
        return await self(methods.messages.GetMessagesInterval(object_guid, middle_message_id))

    async def get_message_url(self, object_guid: str, message_id: int):
        if type(message_id) == str:
            message_id = int(message_id)
        return await self(methods.messages.GetMessageShareUrl(object_guid, message_id))

# ---------------- Channels Methods ----------------

    async def add_channel(self, title: str, description: str = None):
        return await self(methods.channels.AddChannel(title, description))

    async def remove_channel(self, channel_guid: str):
        return await self(methods.channels.RemoveChannel(channel_guid))

    async def get_channel_info(self, channel_guid: str):
        return await self(methods.channels.GetChannelInfo(channel_guid))

    async def edit_channel_info(self,
            channel_guid: str,
            title: str = None,
            description: str = None,
            channel_type: str = None,
            sign_messages: str = None,
    ):
        updated_parameters = []

        if title:
            updated_parameters.append('title')
        if description:
            updated_parameters.append('description')
        if channel_type:
            updated_parameters.append('channel_type')
        if sign_messages:
            updated_parameters.append('sign_messages')

        return await self(methods.channels.EditChannelInfo(
            channel_guid, updated_parameters, title, description, channel_type, sign_messages))

    async def join_channel(self, channel_guid: str):
        return await self(methods.channels.JoinChannelAction(channel_guid, 'Join'))

    async def leave_channel(self, channel_guid: str):
        return await self(methods.channels.JoinChannelAction(channel_guid, 'Remove'))

    async def archive_channel(self, channel_guid: str):
        return await self(methods.channels.JoinChannelAction(channel_guid, 'Archive'))

    async def join_channel_by_link(self, link: str):
        return await self(methods.channels.JoinChannelByLink(link))

    async def add_channel_members(self, channel_guid: str, member_guids: list):
        return await self(methods.channels.AddChannelMembers(channel_guid, member_guids))

    async def ban_channel_member(self, channel_guid: str, member_guid: str):
        return await self(methods.channels.BanChannelMember(channel_guid, member_guid, 'Set'))

    async def unban_channel_member(self, channel_guid: str, member_guid: str):
        return await self(methods.channels.BanChannelMember(channel_guid, member_guid, 'Unset'))

    async def check_channel_username(self, username: str):
        return await self(methods.channels.CheckChannelUsername(username))

    async def channel_preview_by_join_link(self, link: str):
        return await self(methods.channels.ChannelPreviewByJoinLink(link))

    async def get_channel_all_members(self, channel_guid: str, search_text: str = None, start_id: int = None):
        return await self(methods.channels.GetChannelAllMembers(channel_guid, search_text, start_id))

    async def get_channel_admin_members(self, channel_guid: str, start_id: int = None):
        return await self(methods.channels.GetChannelAdminMembers(channel_guid, start_id))

    async def update_channel_username(self, channel_guid: str, username: str):
        return await self(methods.channels.UpdateChannelUsername(channel_guid, username))

    async def get_channel_link(self, channel_guid: str):
        return await self(methods.channels.GetChannelLink(channel_guid))

    async def set_channel_link(self, channel_guid: str):
        return await self(methods.channels.SetChannelLink(channel_guid))

    async def get_channel_admin_access_list(self, channel_guid: str, member_guid: str):
        return await self(methods.channels.GetChannelAdminAccessList(channel_guid, member_guid))

# ---------------- Contacts Methods ----------------

    async def delete_contact(self, user_guid: str):
        return await self(methods.contacts.DeleteContact(user_guid))

    async def add_address_book(self, phone: str, first_name: str, last_name: str = ''):
        return await self(methods.contacts.AddAddressBook(phone, first_name, last_name))

    async def get_contacts_updates(self, state: int = None):
        return await self(methods.contacts.GetContactsUpdates(state))

    async def get_contacts(self, start_id: int = None):
        return await self(methods.contacts.GetContacts(start_id))

# ---------------- Settings Methods ----------------

    async def set_setting(self,
            show_my_last_online: str = None,
            show_my_phone_number: str = None,
            show_my_profile_photo: str = None,
            link_forward_message: str = None,
            can_join_chat_by: str = None
    ):
        updated_parameters = []

        if show_my_last_online:
            updated_parameters.append('show_my_last_online')
        if show_my_phone_number:
            updated_parameters.append('show_my_phone_number')
        if show_my_profile_photo:
            updated_parameters.append('show_my_profile_photo')
        if link_forward_message:
            updated_parameters.append('link_forward_message')
        if can_join_chat_by:
            updated_parameters.append('can_join_chat_by')

        return await self(methods.settings.SetSetting(
            updated_parameters,
            show_my_last_online,
            show_my_phone_number,
            show_my_profile_photo,
            link_forward_message,
            can_join_chat_by))

    async def add_folder(self,
            include_chat_types: list = None,
            exclude_chat_types: list = None,
            include_object_guids: list = None,
            exclude_object_guids: list = None
    ):
        return await self(methods.settings.AddFolder(
            include_chat_types,
            exclude_chat_types,
            include_object_guids,
            exclude_object_guids))

    async def get_folders(self, last_state: int):
        return await self(methods.settings.GetFolders(last_state))

    async def edit_folder(self,
            include_chat_types: list = None,
            exclude_chat_types: list = None,
            include_object_guids: list = None,
            exclude_object_guids: list = None
    ):
        updated_parameters = []

        if include_chat_types:
            updated_parameters.append('include_chat_types')
        if exclude_chat_types:
            updated_parameters.append('exclude_chat_types')
        if include_object_guids:
            updated_parameters.append('include_object_guids')
        if exclude_object_guids:
            updated_parameters.append('exclude_object_guids')

        return await self(methods.settings.EditFolder(
            updated_parameters,
            include_chat_types,
            exclude_chat_types,
            include_object_guids,
            exclude_object_guids))

    async def delete_folder(self, folder_id: str):
        return await self(methods.settings.DeleteFolder(folder_id))

    async def update_profile(self, first_name: str = None, last_name: str = None, bio: str = None):
        updated_parameters = []

        if first_name:
            updated_parameters.append('first_name')
        if last_name:
            updated_parameters.append('last_name')
        if bio:
            updated_parameters.append('bio')

        return await self(methods.settings.UpdateProfile(updated_parameters, first_name, last_name, bio))

    async def update_username(self, username: str):
        return await self(methods.settings.UpdateUsername(username))

    async def get_two_passcode_status(self):
        return await self(methods.settings.GetTwoPasscodeStatus())

    async def get_suggested_folders(self):
        return await self(methods.settings.GetSuggestedFolders())

    async def get_privacy_setting(self):
        return await self(methods.settings.GetPrivacySetting())

    async def get_blocked_users(self):
        return await self(methods.settings.GetBlockedUsers())

    async def get_my_sessions(self):
        return await self(methods.settings.GetMySessions())

    async def terminate_session(self, session_key: str):
        return await self(methods.settings.TerminateSession(session_key))

    async def setup_two_step_verification(self, password: str, hint: str, recovery_email: str):
        return await self(methods.settings.SetupTwoStepVerification(password, hint, recovery_email))

# ---------------- Stickers Methods ----------------

    async def get_my_sticker_sets(self):
        return await self(methods.stickers.GetMyStickerSets())

    async def search_stickers(self, search_text: str = '', start_id: int = None):
        return await self(methods.stickers.SearchStickers(search_text, start_id))

    async def get_sticker_set_by_ID(self, sticker_set_id: str):
        return await self(methods.stickers.GetStickerSetByID(sticker_set_id))

    async def action_on_sticker_set(self, sticker_set_id: str, action: str = 'Add'):
        return await self(methods.stickers.ActionOnStickerSet(sticker_set_id, action))

    async def get_stickers_by_emoji(self, emoji: str, suggest_by: str = 'Add'):
        return await self(methods.stickers.GetStickersByEmoji(emoji, suggest_by))

    async def get_stickers_by_set_IDs(self, sticker_set_ids: list):
        return await self(methods.stickers.GetStickersBySetIDs(sticker_set_ids))

    async def get_trend_sticker_sets(self, start_id: int = None):
        return await self(methods.stickers.GetTrendStickerSets(start_id))