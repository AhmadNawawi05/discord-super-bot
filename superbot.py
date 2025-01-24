import asyncio
import os
import re
import urllib.parse
import urllib.request

import discord
import yt_dlp
from discord import voice_client
from discord.ext import commands
from dotenv import load_dotenv


def run_bot():
    load_dotenv()
    token = os.getenv("discord_token")
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix='.', intents=intents)
    
    queues = {}
    voice_clients = {}
    yt_base_url = 'https://www.youtube.com/'
    yt_result_url = yt_base_url + 'results?'
    yt_watch_url = yt_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    
    @client.event
    async def on_ready():
        print(f'{client.user} is ready to serve!')

    @client.command(name="play")
    async def play(ctx, *, link):
        try:
            if ctx.guild.id not in voice_client or not voice_client[ctx.guild.id].is_connected():
                voice_client[ctx.guild.id] = await ctx.author.voice.channel.connect()

            if yt_base_url not in link:
                query_string = urllib.parse.urlencode({"search_query": link})
                content = urllib.request.urlopen(yt_result_url + query_string)
                search_result = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                link = yt_watch_url + search_result[0]

            if ctx.guild.id not in queues:
                queues[ctx.guild.id] = []

            if voice_client[ctx.guild.id].is_playing():
                queues[ctx.guild.id].append(link)
                await ctx.send("Song added to the queue!")
                return

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
            song = data['url']

            player = discord.FFmpegOpusAudio(song, executable="C:\\ffmpeg\\ffmpeg.exe", **ffmpeg_options)
            voice_client[ctx.guild.id].play(
                player,
                after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop)
            )

            await ctx.send(f"Now playing: {data['title']}")

        except Exception as e:
            print(e)

    async def play_next(ctx):
        if queues[ctx.guild.id]:
            link = queues[ctx.guild.id].pop(0)
            await play(ctx, link=link)
        else:
            await ctx.send("Queue is empty. No more songs to play!")

    @client.command(name="queue")
    async def queue(ctx, *, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue.")

    @client.command(name="skip")
    async def skip(ctx):
        try : 
            if voice_clients[ctx.guild.id].is_playing():
                voice_clients[ctx.guild.id].stop()
                await ctx.send("Skipped to next song")
            else: 
                await ctx.send("No song is curently playing")
        except Exception as e:
            print(e)
    
    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        queues[ctx.guild.id] = []
        await ctx.send("The queue has been cleared.")
    
    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
            await ctx.send("Playback paused.")
        except Exception as e:
            print(e)
    
    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
            await ctx.send("Playback resumed.")
        except Exception as e:
            print(e)
    
    @client.command(name="stop")
    async def stop(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
            await ctx.send("Playback stopped and disconnected from the voice channel.")
        except Exception as e:
            print(e)
    
    client.run(token)