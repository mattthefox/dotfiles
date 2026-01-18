'''
Copyright (C) Denys Hsu, cgtinker, cgtinker.com, hello@cgtinker.com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import logging
import bpy
import queue
from .b3dnet.src.b3dnet import connection as bnc
from .b3dnet.src.b3dnet import request as bnr
from typing import Optional

bl_info = {
    "name":        "BlendArSock",
    "description": "Local network implementation via tcp.",
    "author":      "cgtinker",
    "version":     (0, 0, 1),
    "blender":     (3, 0, 0),
    "location":    "3D View > Tool",
    "doc_url":     "https://cgtinker.github.io/BlendArSock/",
    "tracker_url": "https://github.com/cgtinker/BlendArSock/issues",
    "support":     "COMMUNITY",
    "category":    "Development"
}

QUEUE: queue.Queue[bnr.Task] = queue.Queue()
logging.getLogger().setLevel(logging.DEBUG)


class PG_CGT_BlendArSock_Properties(bpy.types.PropertyGroup):
    port: bpy.props.IntProperty(  # type: ignore
        default=6000, soft_min=1000, soft_max=9999,
        description="Choose an open port number."
    )

    authkey: bpy.props.StringProperty(  # type: ignore
        default="", subtype='PASSWORD',
        description="Choose a password for incoming connections."
    )

    blocktime: bpy.props.FloatProperty(  # type: ignore
        default=10.0, soft_min=1.0, soft_max=60.0,
        description="Starting up the server blocks Blender. Set a timeout."
    )

    host: bpy.props.StringProperty(  # type: ignore
        default="localhost", description="Internal Property, may be resetted."
    )

    server_active: bpy.props.BoolProperty(  # type: ignore
        default=False, description="Internal Property for synchronisation."
    )


class WM_OT_TCPServer(bpy.types.Operator):
    bl_label = "Server"
    bl_idname = "wm.ot_cgt_tcp_server"
    bl_description = "Server to receive request from external executables."

    _timer: Optional[bpy.types.Timer] = None
    server: bnc.TCPServer
    pendeling: bool

    @classmethod
    def poll(cls, context):
        # Clean entry point, even if it should not matter where
        # request are getting received. We can change the mode anyways.
        return context.mode in {'OBJECT'}

    def execute(self, context):
        self.user = getattr(context.scene, "cgt_blendarsock")
        if self.user.server_active:
            self.user.server_active = False
            return {'FINISHED'}

        auth = self.user.authkey
        assert self.user.port > 0

        # Initialize the server
        self.server = bnc.TCPServer(
            self.user.host,
            self.user.port,
            QUEUE,
            auth.encode('utf-8') if auth is not None else None
        )

        # Try to connect - TODO: What are regular errors on windows?
        try:
            block = self.user.blocktime
            self.server.connect(
                timeout=block if block > 0 and block < 360 else 5
            )
        except OSError:
            self.report({'ERROR'},
                        "Port is blocked by another Process. \
                        If you've been using the Port in a previous session, restart Blender. \
                        Otherwise choose another port as it may be used by another application."
                        )
            return {'CANCELLED'}

        # Start the modal if an connection has been established
        if self.server.running.is_set():
            self.user.server_active = True
            self.re_set_timer(context, 0.0)
            wm = context.window_manager
            wm.modal_handler_add(self)
            self.pendeling = False
            return {'RUNNING_MODAL'}

        # Close the socket to reuse the port.
        self.server.server_close()
        self.user.server_active = False
        self.report(
            {'INFO'}, "Didn't receive any incoming connections, shutting down."
        )
        return {'FINISHED'}

    def modal(self, context, event):
        if not event.type == 'TIMER':
            # Only execute on timer updates.
            return {'PASS_THROUGH'}

        # Shutdown on errors or server shutdown state
        if self.server.flag & (bnc.SERVER.SHUTDOWN | bnc.SERVER.ERROR)  \
                or not self.user.server_active:
            self.cancel(context)
            return {'CANCELLED'}

        # While q.size is not reliable, it's good enough.
        # It doesn't matter if the queued task gets executed a frame later.
        if QUEUE.qsize == 0:
            return {'PASS_THROUGH'}

        # Try getting the next task from the queue.
        try:
            request = QUEUE.get(block=False)
        except queue.Empty:
            request = None
            pass

        if not request or not request.flag:
            return {'PASS_THROUGH'}

        # Check for server related requests.
        # 1. Shutdown server.
        elif request.flag & bnr.TASK.SHUTDOWN:
            self.cancel(context)
            return {'CANCELLED'}

        # 2. Restart server.
        # Change the modals callback time to save resources
        # when waiting for new connections.
        elif request.flag & bnr.TASK.RESTART:
            self.re_set_timer(context, 1.0)
            self.pendeling = True

        # 3. Server pendeling and received request
        # If the server is pendeling, set the callback back to zero.
        elif request and self.pendeling:
            self.re_set_timer(context, 0.0)
            self.pendeling = False

        # Execute the request.
        request.execute()
        QUEUE.task_done()

        return {'PASS_THROUGH'}

    def cancel(self, context):
        # Remove the wm timer.
        self.user.server_active = False
        self.remove_timer(context)

        # Stop running the server.
        if hasattr(self, "server") and hasattr(self.server, "running"):
            self.server.flag = bnc.SERVER.SHUTDOWN
            self.server.server_close()

        # Flush the queue. Ignore staged tasks.
        while True:
            try:
                _ = QUEUE.get_nowait()
                QUEUE.task_done()
            except queue.Empty:
                break

    def remove_timer(self, context):
        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
            self._timer = None

    def re_set_timer(self, context, timestep: float):
        # Reset or add a timer.
        wm = context.window_manager
        self.remove_timer(context)
        self._timer = wm.event_timer_add(timestep, window=context.window)


class PT_UI_CGT_Connection_Panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BlendAR"
    bl_options = {'DEFAULT_CLOSED'}
    bl_label = "Connection"
    bl_idname = "UI_PT_CGT_TCPConnection"

    def draw(self, context):
        user = getattr(context.scene, "cgt_blendarsock")
        layout = self.layout

        if user.server_active:
            layout.row().operator("wm.ot_cgt_tcp_server", text="Shutdown Server", icon="CANCEL")
        elif not user.server_active:
            layout.row().operator("wm.ot_cgt_tcp_server", text="Start Server", icon="NONE")

        col = layout.column(align=True)
        if context.preferences.view.show_developer_ui:
            col.row(align=True).prop(data=user, property="host", text="Host")
        col.row(align=True).prop(data=user, property="port", text="Port")
        col.row(align=True).prop(
            data=user, property="blocktime", text="Block")
        col.separator()

        col.row(align=True).prop(data=user, property="authkey", text="Pass")


classes = [
    PG_CGT_BlendArSock_Properties,
    WM_OT_TCPServer,
    PT_UI_CGT_Connection_Panel,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    properties = bpy.props.PointerProperty(type=PG_CGT_BlendArSock_Properties)
    setattr(bpy.types.Scene, "cgt_blendarsock", properties)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    delattr(bpy.types.Scene, "cgt_blendarsock")


if __name__ == '__main__':
    try:
        unregister()
    except RuntimeError:
        pass

    register()
