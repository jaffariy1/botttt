import disnake
from disnake.ext import commands, tasks
import youtube_dl
import random
import asyncio
import nacl

__TOKEN__ = 'MTIyOTQyMDQ1NTkzMzM3ODU3MA.GDJ2mT.sEwvDvWoB21aeq3YDaySpETDrOzl_MpL_-8WF4'
ffmpeglink = "F:\PycharmProjects\pythonProject1\pffmpeg\pin\pfmpeg.exe"
song_queue = []

tasker = None
intents = disnake.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True
bot = commands.Bot(command_prefix='.', intents=intents)
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdloptions = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'extractaudio': True,
    'audioformat': 'mp3',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
ytdl = youtube_dl.YoutubeDL(ytdloptions)

class plvid(disnake.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.duration = data.get('duration')
        self.url = data.get('webpage_url')
        self.thumbnail = data.get('thumbnail')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, play=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None,
                                          lambda: ytdl.extract_info(f"ytsearch:{url}", download=not stream or play))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(disnake.FFmpegPCMAudio(filename, executable=ffmpeglink), data=data)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')


@bot.command(name='play', aliases=['p', 'play_song'], help='Используйте эту команду, чтобы проиграть песню по ссылке.')
async def play(ctx: commands.Context, *, url: str):
    global song_queue
    voice = disnake.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice is None and not ctx.author.voice:
        embed = disnake.Embed(title="🚫 Ошибка",
                              description="⚠️ Вы не в войс-канале.",
                              color=0xff0000)
        await ctx.send(embed=embed)
        return

    if voice is None:
        channel = ctx.author.voice.channel
        await channel.connect()
        voice = disnake.utils.get(bot.voice_clients, guild=ctx.guild)

    async with ctx.typing():
        try:
            player = await plvid.from_url(url, loop=bot.loop, stream=True)
            if not voice.is_playing():
                song_queue.append(player)
                await start_playing(ctx, voice, song_queue)
                embed = disnake.Embed(title="🎶 Сейчас играет",
                                      description=f"🎵 {player.title}",
                                      color=0x00ff00)
                embed.set_thumbnail(url=player.thumbnail)
                await ctx.send(embed=embed)
            else:
                song_queue.append(player)
                embed = disnake.Embed(title="🎵 Добавлено в очередь",
                                      description=f"{player.title}",
                                      color=0x00ff00)
                embed.set_thumbnail(url=player.thumbnail)
                await ctx.send(embed=embed)
        except Exception as e:
            embed = disnake.Embed(title="🚫 Ошибка",
                                  description=f"⚠️ Произошла ошибка: {e}",
                                  color=0xff0000)
            await ctx.send(embed=embed)


async def start_playing(ctx, voice, song_queue):
    while song_queue:
        player = song_queue.pop(0)
        voice.play(player, after=lambda e: start_playing(ctx, voice, song_queue) if song_queue else None)
        embed = disnake.Embed(title="🎵 Сейчас играет",
                              description=f"🎶 {player.title}",
                              color=0x1DB954)
        embed.set_thumbnail(url=player.thumbnail)
        await ctx.send(embed=embed)
        while voice.is_playing() or voice.is_paused():
            await asyncio.sleep(1)



@bot.command(name='now_playing', aliases=['np'], help='Показывает текущий проигрываемый трек.')
async def now_playing(ctx: commands.Context):
    if song_queue:
        player = song_queue[0]
        embed = disnake.Embed(title="🎶 Сейчас проигрывается",
                              description=f"{player.title}",
                              color=0x1DB954)
        embed.set_thumbnail(url=player.thumbnail)
    else:
        embed = disnake.Embed(title="🎶 Сейчас проигрывается",
                              description="В данный момент ничего не играет.",
                              color=0xff0000)
    await ctx.send(embed=embed)


@bot.command(name='repeat', help='Повторяет текущий трек.')
async def repeat(ctx: commands.Context):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing() and song_queue:
        song_queue.insert(0, song_queue[0])
        embed = disnake.Embed(title="🔂 Повтор трека",
                              description=f"Трек {song_queue[0].title} будет повторён.",
                              color=0x1DB954)
        embed.set_thumbnail(url=song_queue[0].thumbnail)
    else:
        embed = disnake.Embed(title="🔂 Повтор трека",
                              description="В данный момент нет трека для повторения.",
                              color=0xff0000)
    await ctx.send(embed=embed)


@bot.command(name='leave', aliases=['l', 'exit'], help='Используйте эту команду, чтобы заставить бота выйти из '
                                                       'голосового канала.')
async def leave(ctx: commands.Context):
    title_leave = "🎶 Отключение..."
    descr_leave = "Процесс отключения от голосового канала запущен."
    descr_not_connected = "⚠️ Бот не в голосовом канале, нет необходимости в отключении."
    color_success = 0x1DB954
    color_warning = 0xFF0000
    embed = disnake.Embed(title=title_leave,
                          description=descr_leave,
                          color=color_success)
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        embed.description = f"✅ Успешно отключён от голосового канала."
    else:
        embed.description = descr_not_connected
        embed.color = color_warning
    await ctx.send(embed=embed)


@bot.command(name='pause', help='Поставить текущую песню на паузу.')
async def pause(ctx: commands.Context):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        embed = disnake.Embed(title="⏸️ Пауза",
                              description="🎵 Музыка приостановлена.",
                              color=0x1DB954)
        voice_client.pause()
    else:
        embed = disnake.Embed(title="🚫 Ошибка",
                              description="🔇 Музыка не воспроизводится.",
                              color=0xff0000)
    await ctx.send(embed=embed)


@bot.command(name='resume', help='Продолжить воспроизведение песни после паузы.')
async def resume(ctx: commands.Context):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_paused():
        embed = disnake.Embed(title="▶️ Воспроизведение",
                              description="🎶 Музыка возобновлена.",
                              color=0x1DB954)
        voice_client.resume()
    else:
        embed = disnake.Embed(title="🚫 Ошибка",
                              description="🔇 Нет музыки на паузе.",
                              color=0xff0000)
    await ctx.send(embed=embed)


@bot.command(name='stop', help='Остановить воспроизведение музыки и очистить очередь.')
async def stop(ctx: commands.Context):
    global song_queue
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        embed = disnake.Embed(title="⏹️ Остановка",
                              description="🎵 Воспроизведение и очередь треков очищены.",
                              color=0x1DB954)
        song_queue.clear()
        voice_client.stop()
    else:
        embed = disnake.Embed(title="🚫 Ошибка",
                              description="🔇 Не воспроизводится никакая музыка.",
                              color=0xff0000)
    await ctx.send(embed=embed)


@bot.command(name='skip', help='Пропустить текущий трек и перейти к следующему в очереди.')
async def skip(ctx: commands.Context):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        if song_queue:
            song_queue.pop(0)
        embed = disnake.Embed(title="⏭️ Пропуск",
                              description="🎶 Трек пропущен. Перехожу к следующему...",
                              color=0x1DB954)
    else:
        embed = disnake.Embed(title="🚫 Ошибка",
                              description="🔇 Не воспроизводится никакая музыка.",
                              color=0xff0000)
    await ctx.send(embed=embed)


@bot.command(name='queued', aliases=['q', 'list'], help='Показать все треки в очереди.')
async def queued(ctx: commands.Context):
    embed = disnake.Embed(title="📜 Очередь треков",
                          color=0x1DB954)
    if song_queue:
        embed.description = "\n".join(f"**#{i}.** {player.title}" for i, player in enumerate(song_queue, start=1))
    else:
        embed.description = "🔇 В очереди нет треков."
    await ctx.send(embed=embed)


@bot.command(name='shuffle', help='Перемешать треки в очереди.')
async def shuffle(ctx: commands.Context):
    global song_queue
    if len(song_queue) > 1:
        random.shuffle(song_queue)
        embed = disnake.Embed(title="🔀 Перемешивание",
                              description="Очередь треков была перемешана.",
                              color=0x1DB954)
    else:
        embed = disnake.Embed(title="🚫 Ошибка",
                              description="🔇 Недостаточно треков в очереди для перемешивания.",
                              color=0xff0000)
    await ctx.send(embed=embed)


@bot.command(name='search', help='Поиск музыки по ключевым словам.')
async def search(ctx: commands.Context, *, search_query: str):
    search_results = await plvid.from_url(search_query, loop=bot.loop, stream=True, play=False)
    if 'entries' in search_results and search_results['entries']:
        description = "\n".join(f"**#{i+1}.** {entry['title']}" for i, entry in enumerate(search_results['entries'], start=1))
        embed = disnake.Embed(title="🔎 Результаты Поиска",
                              description=description,
                              color=0x1DB954)
    else:
        embed = disnake.Embed(title="🔎 Результаты Поиска",
                              description="Ваш запрос не дал результатов.",
                              color=0xff0000)
    await ctx.send(embed=embed)

bot.run(__TOKEN__)
