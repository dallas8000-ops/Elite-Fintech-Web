import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from billing.services.events import org_group_name


class BillingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        org_id = self.scope.get("organization_id")
        user = self.scope.get("user")

        if not org_id or not user or not user.is_authenticated:
            await self.close()
            return

        self.org_id = org_id
        self.group = org_group_name(org_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json(
            {
                "type": "connected",
                "organizationId": org_id,
                "role": self.scope.get("role"),
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def billing_event(self, event):
        await self.send_json({"event": event["event"], "data": event["data"]})
