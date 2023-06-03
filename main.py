import discord, requests, json
from discord.ext import commands
from discord.ext.commands import BucketType

class Bot:     
    def __init__(self):
        self.config = self._config
    
    @property
    def _config(self):
        with open("config.json") as f: return json.load(f)
        
    async def check_item(self, item_id: str):
        if item_id in self.config["items"]["items_checked"] and not self.config["items"]["items_checked"] >= int(item_id):
            item = self.config["items"]["items_checked"][item_id]
            data = {}
            if item["has_location"]:
                data["has_location"] = True
                data["location"] = item["location"]
            else:
                data["has_location"] = False
            return {"success": True, "data": data}
        else:
            return {"success": False}
        
        
    def run(self):
        bot = discord.Bot(intents=discord.Intents.all())
        
        @bot.event
        async def on_ready():
            print("Bot online")
        
        @bot.command(description = "get game id linked to a item")
        @commands.cooldown(1, 60, BucketType.user)
        async def lookup(ctx, item_id: int):
            await ctx.defer()
            check_item = await self.check_item(item_id)
            if check_item["success"]:
                if check_item["data"]["has_location"]:
                    return await ctx.resond(check_item["data"]["location"])
                else:
                    return await ctx.respond("This item id has no game linked to it.")
            else:
                first = requests.get(f"https://economy.roblox.com/v2/assets/{item_id}/details", cookies={".ROBLOSECURITY": self.config["discord"]["cookie"]})
                if first.status_code != 200:
                    return await ctx.respond("Failed to gather information / ratelimit")
                else:
                    if (first.json())["SaleLocation"] is None or len((first.json())["SaleLocation"].get("UniverseIds", [])) == 0:
                        self.config["items"]["items_checked"][str(item_id)] = {"has_location": False}
                        with open("config.json", "w") as f: json.dump(self.config, f, indent=4)
                        return await ctx.respond("This item has no game linked")
                    else:
                        universe_ids = (first.json())['SaleLocation'].get('UniverseIds', [])
                        second = requests.get(f"https://games.roblox.com/v1/games?universeIds={','.join(str(id) for id in universe_ids)}", cookies={".ROBLOSECURITY": self.config["discord"]["cookie"]})
                        if second.status_code != 200:
                            return await ctx.respond("Failed to gather information / ratelimit")
                        else:
                            game_list = []
                            for current in (second.json())["data"]:
                                game_list.append(current['rootPlaceId'])
                                self.config["items"]["items_checked"][str(item_id)] = {"has_location": True,  "location": {"game_universe_id": current["id"], "game_id": current["rootPlaceId"]}}
                            with open("config.json", "w") as f: json.dump(self.config, f, indent=4)
                            return await ctx.respond(f"https://www.roblox.com/games/{', https://www.roblox.com/games/'.join(str(id) for id in game_list)}")
                                
        @lookup.error
        async def my_command_error(ctx, error):
            if isinstance(error, commands.CommandOnCooldown):
                return await ctx.respond(f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.", ephemeral=True)
            print(error)
       
        bot.run(self.config["discord"]["token"])


Bot().run()