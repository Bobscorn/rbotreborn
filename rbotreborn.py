import discord
import asyncio
from discord.ext import commands
import praw
import logging
import config
from gfycat import Gfycat
from custom_embeds import *
from reddit import *
from exceptions import *
from processors import *
Config = config.Config('config.ini')
bot = commands.Bot(command_prefix=Config.bot_prefix,
                   description='R-BotReborn\n https://github.com/colethedj/rbotreborn')


@bot.command(pass_context=True, description="Get x amount of comments from the last post")
async def rcl(ctx, *comment_count:int):
    await bot.delete_message(ctx.message)

    if comment_count:
        comment_count = comment_count[0]
        if comment_count > Config.r_max_comment_count:
            comment_count = Config.r_max_comment_count
    else:
        comment_count = Config.r_default_comment_count
    loading_message = RedditLoadingEmbed()
    loading_message.create_embed(subreddit='unknown', post_count=1,
                                 comment_count=comment_count,
                                 custom_message="Getting comments... This will take a moment")
    bot_message = await bot.send_message(ctx.message.channel, embed=loading_message.get_embed())

    try:
        post_id = Config.r_last_post_url[ctx.message.server.id][ctx.message.channel.id]
        getcomments = Reddit(reddit2)
        comments = getcomments.get_comments(post_id, comment_count)
        embed = RedditCommentEmbed()
        embed.create_embed(comments=comments)
    except KeyError:
        embed = RedditErrorEmbed()
        embed.create_embed(title=":warning: There is no last post from this channel saved",
                           )
    except UnknownException as e:
        embed = RedditErrorEmbed()
        embed.create_embed(title=":warning: Error getting comments from that post: " + str(e),
                           )
        # no saved post from this channel

    await bot.edit_message(bot_message, embed=embed.get_embed())


@bot.command(pass_context=True, description="Get posts from a Reddit comments link. "
                                            "Can also grab comments from that post")
async def ru(ctx, url: str, *comment_count:int):

    if comment_count:
        comment_count = comment_count[0]
        if comment_count > Config.r_max_comment_count:
            comment_count = Config.r_max_comment_count
    else:
        comment_count = 0
    await reddit_handler(ctx, url=url, comment_num=comment_count)


@bot.command(pass_context=True, description="Get posts with comments from Reddit")
async def rc(ctx, subreddit: str, *comment_count: int):
    if comment_count:
        comment_count = comment_count[0]
        if comment_count > Config.r_max_comment_count:
            comment_count = Config.r_max_comment_count
    else:
        comment_count = Config.r_default_comment_count

    await reddit_handler(ctx, subreddit=subreddit, post_count=Config.r_postcount, comment_num=comment_count)


@bot.command(pass_context=True, description="Get posts from reddit (any type)")
async def r(ctx, subreddit: str, *post_count: int):
    if post_count:
        post_count = post_count[0]
    else:
        post_count = Config.r_postcount

    await reddit_handler(ctx, subreddit=subreddit, post_count=post_count, image=None)


@bot.command(pass_context=True, description="Get image-only posts from reddit")
async def ri(ctx, subreddit: str, *post_count: int):
    if post_count:
        post_count = post_count[0]
    else:
        post_count = Config.r_postcount

    await reddit_handler(ctx, subreddit=subreddit, post_count=post_count, image=True)


@bot.command(pass_context=True, description="Get text-only posts from reddit")
async def rt(ctx, subreddit: str, *post_count: int):
    # TODO
    if post_count:
        post_count = post_count[0]
    else:
        post_count = Config.r_postcount

    await reddit_handler(ctx, subreddit=subreddit, post_count=post_count, image=False)


# where all the reddit commands use

# REQUEST TYPES: 'default', 'url'
async def reddit_handler(ctx, **kwargs):

    subreddit = kwargs.get('subreddit', None)
    url = kwargs.get('url', None)
    post_count = int(kwargs.get('post_count', 1))
    image = kwargs.get('image', None)
    comment_num = int(kwargs.get('comment_num', 0))
    request_type = 'default'
    if subreddit is not None:
        subreddit = subreddit.lower()

    if url is not None:
        request_type = 'url'
    # this is already done in reddit.py but we want to show how much posts we are getting in chat
    if post_count is not None:
        if post_count > Config.r_maxpostcount:
            post_count = Config.r_maxpostcount
    else:
        post_count = 1
    # delete the request message
    await bot.delete_message(ctx.message)

    # send a message to show the requester whats happening

    loading_message = RedditLoadingEmbed()
    loading_message.create_embed(subreddit=('unknown' if subreddit is None else subreddit), post_count=post_count, comment_count=comment_num)
    bot_message = await bot.send_message(ctx.message.channel, embed=loading_message.get_embed())
    # check if discord channel is marked as NSFW

    if str(ctx.message.channel.id) in Config.nsfw_channels[ctx.message.server.id]:
        nsfw = True
    else:
        nsfw = False

    # start off with getting posts
    red = Reddit(reddit2)
    error_embed = None
    try:

        post, comments = await red.get(subreddit=subreddit,
                                       post_count=post_count,
                                       nsfw=nsfw,
                                       get_image=image,
                                       comment_count=comment_num,
                                       request_type=request_type,
                                       url=url)

    except SubredditNotExist:
        error_embed = RedditErrorEmbed()
        error_embed.create_embed(title="r/" + str(subreddit) + " does not exist.",
                                 description="check your spelling")
    except SubredditIsNSFW:
        error_embed = RedditErrorEmbed()
        error_embed.create_embed(title="r/" + str(subreddit) + " is a NSFW subreddit",
                                 description="This channel is not set as a NSFW channel. "
                                             "If you want to add this channel as a NSFW channel, "
                                             "use the command -addnsfw.")
    except NoPostsReturned:
        error_embed = RedditErrorEmbed()
        error_embed.create_embed(title="No Posts Returned",
                                 description="Maybe try again with larger post count. "
                                             "If you are getting only images or only text,"
                                             " some subreddits may not have e.g only images.")

    except InvalidRedditURL:
        error_embed = RedditErrorEmbed()
        error_embed.create_embed(title="Invalid Reddit Submission URL entered",
                                 description="Make sure the URL you entered is correct and links "
                                             "to a post.")

    except RedditOAuthException as e:
        error_embed = RedditErrorEmbed()
        error_embed.create_embed(title="Reddit Authentication Failure",
                                 description="Make sure you have enter credentials and that they are correct"
                                             "in the config file. Also make sure only application using your "
                                             "API credentials at once. " + str(e))
    except UnknownException as e:
        error_embed = RedditErrorEmbed()
        error_embed.create_embed(title="Unknown Error",
                                 description="""R-BOT has not been programmed to handle this error.
                                             Error Output: """ + str(e))

    finally:
        if error_embed is not None:
            await bot.edit_message(bot_message, embed=error_embed.get_embed())
            return
    # TODO: ERROR HANDLERS
    # handle the post types

    post_type = post.get('post_type')
    post_text = post.get('post_text')
    post_id = post.get('post_id')
    image_url = "NONE"  # had issues with None being turned to a str type for some reason
    if post_type != "link" and post_type != "reddit":

        if post_type != "gif" and post_type != "image":

            if post_type == "gfycat":

                post_gfycat = Gfycat(Config.gfycat_client_id, Config.gfycat_client_secret)
                gfyjson = await post_gfycat.get_gfy_info(str(post.get('post_url'))[19:(len(str(post.get('post_url'))))])
                print(gfyjson)  # TODO: fails if starts with http://
                image_url = gfyjson['gfyItem']['max5mbGif']
                # TODO: maybe some error handling here?
            elif post_type == "imgur":

                post['post_text'] = "R-BotReborn: Imgur Links are not supported yet"

            else:

                processing_embed = GfycatLoadingEmbed()
                await bot.edit_message(bot_message, embed=processing_embed.get_embed())

                image_url = await gfycat_url_handler(post.get('post_url'))

                if image_url is GfycatErrorEmbed:
                        # time to send error to channel
                        await bot.edit_message(bot_message, embed=error_embed.get_embed())
                        image_url = None
                        return

        elif post_type == "gif" or post_type == "image":  # either gif or image

            image_url = post.get('post_url')

    elif post_type == "link":

        if Config.enable_sumy:
            # tldrify if user wants
            # TODO: add this function
            # we are going to TLDRify the link (but only if there is not text to start with)
            if post_text ==  "":
                post_text = "**TL;DR:** " + await sumy_url(post.get('post_url'))


    # create reddit embed
    comment_embed = None
    if len(comments) > 0:
        comment_embed = RedditCommentEmbed()
        comment_embed.create_embed(comments=comments)
    post_embed = RedditPostEmbed()
    post_embed.create_embed(title=str(post.get('post_title')),
                            url=str(post.get('post_permalink')),
                            author=str(post.get('post_author')),
                            nsfw=bool(post.get('nsfw')),
                            score=int(post.get('post_score')),
                            description=str(post_text),
                            image=str(image_url),
                            time=str(post.get('created_utc')) + " UTC",
                            subreddit=str(post.get('post_subreddit'))
                            )



    await bot.edit_message(bot_message, embed=post_embed.get_embed())

    if comment_embed is not None:
        await bot.send_message(ctx.message.channel, embed=comment_embed.get_embed())

    # now we will save the post id

    if str(ctx.message.server.id) in Config.r_last_post_url:
        Config.r_last_post_url[str(ctx.message.server.id)][str(ctx.message.channel.id)] = post_id
    else:
        Config.r_last_post_url[str(ctx.message.server.id)] = {str(ctx.message.channel.id): post_id}



@bot.command(pass_context=True, description="Allow NSFW on current channel")
async def addnsfw(ctx):
    new_channels, message = config.UpdateConfig('config.ini').add_nsfw_channels(str(ctx.message.server.id), str(ctx.message.channel.id))
    Config.nsfw_channels = new_channels

    if message is None:
        embed = discord.Embed(title=":underage: Added this channel as a NSFW Channel")
    else:
        embed = discord.Embed(title=":warning:" + str(message))

    await bot.send_message(ctx.message.channel, embed=embed)


@bot.command(pass_context=True, description="Allow NSFW on current channel")
async def removensfw(ctx):
    new_channels, message = config.UpdateConfig('config.ini').remove_nsfw_channels(str(ctx.message.server.id), str(ctx.message.channel.id))
    Config.nsfw_channels = new_channels

    if message is None:
        embed = discord.Embed(title=":wastebasket: Removed this channel as a NSFW Channel")
    else:
        embed = discord.Embed(title=":warning: " + str(message))

    await bot.send_message(ctx.message.channel, embed=embed)



@bot.event
# when ready display this shit
async def on_ready():
    logging.info('Logged into discord as:')
    logging.info(bot.user.name)
    logging.info(bot.user.id)
    print(vars(reddit2))
    print(dir(reddit2))

    logging.info("Logged into reddit as:")
    #logging.info(reddit2.user.me())

    logging.info('------')
    await bot.change_presence(game=discord.Game(name=Config.bot_game))


# main method run when starting
def start():
    # connect to discord
    print(Config.discord_token)
    bot.run(Config.discord_token)


# connect to reddit (instance)

# connect to reddit (instance)
def connect_reddit():


    reddit = praw.Reddit(client_id=Config.r_client_id,
                         client_secret=Config.r_client_secret,
                         user_agent=Config.r_user_agent,
                        )

    return reddit


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    reddit2 = connect_reddit()

    start()




