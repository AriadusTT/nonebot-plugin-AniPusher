
import json
import asyncio
import re
from typing import Any
import aiohttp
from nonebot import logger
from ....config.global_config import FUNCTION
from ..abstract_processor import AbstractDataProcessor
from ....database.table_structure import DatabaseTables
from ....constants.error_handling import AppError
from ....others.utils import PublicUtils
from ....external import TmdbRequest


@AbstractDataProcessor.register(DatabaseTables.TableName.EMBY)
class EmbyDataProcessor(AbstractDataProcessor):

    async def _reformat(self) -> None:
        try:
            default_dict = DatabaseTables.generate_default_dict(
                self.source)
        except Exception as e:
            raise AppError.Exception(
                AppError.UnknownError, f"{self.source.value}：获取默认模板结构异常：{e}")
        if not self.raw_data:
            raise AppError.Exception(
                AppError.ParamNotFound, f"{self.source.value}：待处理的数据为空")
        if not isinstance(self.raw_data, dict):
            raise AppError.Exception(
                AppError.UnSupportedType, f"{self.source.value}：待处理的数据类型错误：{type(self.raw_data)}")

        try:
            extract = self.DataExtraction(self.raw_data)  # 初始化数据提取类
            # 配置默认项
            send_status = False  # 配置默认发送状态
            timestamp = extract.extract_timestamp()  # 获取时间戳
            item = extract.extract_item()
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, f"{self.source.value}：数据格式不正确，缺少 Item 字段")
            item_type = extract.extract_item_type(item)  # 获取类型
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, f"{self.source.value}：数据格式不正确，缺少 Item Type 字段")
            # 获取标题
            title = extract.extract_title(item_type, item)
            description = extract.extract_description(item)  # 获取描述
            season = extract.extract_season(
                item_type, item)  # 获取season
            episode = extract.extract_episode(
                item_type, item)  # 获取episode
            episode_title = extract.extract_episode_title(
                item_type, item)  # 获取episode标题
            tmdb_id, imdb_id, tvdb_id = await extract.extract_id(item)
            series_id = extract.extract_series_id(
                item_type, item)  # 获取series_id
            season_id = extract.extract_season_id(
                item_type, item)  # 获取season_id
            episode_id = extract.extract_episode_id(
                item_type, item)  # 获取episode_id
            series_tag = extract.extract_series_tag(
                item_type, item)  # 获取series_tag
            episode_tag = extract.extract_episode_tag(
                item_type, item)  # 获取episode_tag
            season_tag = extract.extract_season_tag(
                item_type, item)  # 获取season_tag
            server_id = extract.extract_server_id()  # 获取服务器ID
            server_name = extract.extract_server_name()  # 获取服务器名称
            merged_episode = extract.extract_merged_episode(
                item_type)  # 获取合并推送集数
            raw_data = extract.extract_raw_data()  # 获取原始数据
        except (AppError.Exception, Exception) as e:
            raise AppError.Exception(
                AppError.UnknownError, f"{self.source.value}：数据格式化异常：{e}")
        default_dict.update({
            "send_status": send_status,  # 配置默认发送状态
            "timestamp": timestamp,  # 获取时间戳
            "type": item_type,  # 获取类型
            "title": title,  # 获取标题
            "description": description,  # 获取描述
            # 获取season# 获取season
            "season": season,
            "episode": episode,  # 获取episode
            # 获取episode标题
            "episode_title": episode_title,
            "tmdb_id": tmdb_id,  # 获取themoviedbID
            "imdb_id": imdb_id,  # 获取imdbID
            "tvdb_id": tvdb_id,  # 获取tvdbID
            # 获取series_id# 获取series_id
            "series_id": series_id,
            # 获取season_id# 获取season_id
            "season_id": season_id,
            # 获取episode_id
            "episode_id": episode_id,
            # 获取series_image
            "series_tag": series_tag,
            # 获取season_image
            "episode_tag": episode_tag,
            # 获取episode_image
            "season_tag": season_tag,
            "server_name": server_name,  # Emby服务器名称
            "server_id": server_id,  # Emby服务器ID
            # 获取合并推送集数
            "merged_episode": merged_episode,
            "raw_data": raw_data  # 原始数据
        })
        # 完成数据整形化
        self.reformated_data = default_dict  # 设置整形化后的数据
        self.tmdb_id = tmdb_id  # 设置TMDB ID
        logger.opt(colors=True).info(
            f"<g>{self.source.value}</g>：数据整形化完成，已准备好持久化数据")

    class DataExtraction:
        def __init__(self, data: dict):
            self.data = data

        def extract_timestamp(self) -> str:
            """提取时间戳"""
            return PublicUtils.get_timestamp()

        def extract_item(self) -> Any | None:
            """提取Item"""
            return self.data.get("Item")

        def extract_server(self) -> Any | None:
            """提取服务器信息"""
            return self.data.get("Server")

        def extract_item_type(self, item) -> Any:
            """提取Item类型"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            return item.get("Type")

        def extract_title(self, item_type, item) -> Any | None:
            """提取标题"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return item.get("Name")
            elif item_type == "Episode":
                return item.get("SeriesName")
            else:
                return None

        def extract_description(self, item):
            """提取描述"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            return item.get("Overview")

        def extract_season(self, item_type, item) -> Any | None:
            """提取Season"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return None
            elif item_type == "Episode":
                return item.get("ParentIndexNumber")
            else:
                return None

        def extract_episode(self, item_type, item) -> Any | None:
            """提取Episode"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return None
            elif item_type == "Episode":
                return item.get("IndexNumber")
            else:
                return None

        def extract_episode_title(self, item_type, item) -> Any | None:
            """提取Episode标题"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return None
            elif item_type == "Episode":
                return item.get("Name")
            else:
                return None

        # 注意，该方法为异步方法
        async def extract_id(self, item):
            """提取ID"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            provider_ids = item.get("ProviderIds", {})
            if not provider_ids:
                logger.opt(colors=True).warning(
                    "<y>EMBY</y>： 数据格式不正确，缺少 ProviderIds 字段,将返回空ID")
                return None, None, None
            # 提取不同类型的ID
            imdb_id = provider_ids.get("Imdb")
            tmdb_id = provider_ids.get("Tmdb")
            tvdb_id = provider_ids.get("Tvdb")
            if FUNCTION.tmdb_enabled is False:
                logger.opt(colors=True).warning(
                    "<y>TMDB</y>：功能未启用，无法获取/验证 TMDB ID")
                tmdb_id = None
                return tmdb_id, imdb_id, tvdb_id
            # 如果获取到tmdb_id，尝试验证ID
            if tmdb_id:
                try:
                    check_result = await self._verify_id_from_response(int(tmdb_id))
                    if check_result:
                        logger.opt(colors=True).info(
                            f"<g>EMBY</g>：ID验证通过，tmdb_id: {tmdb_id}")
                    else:
                        logger.opt(colors=True).warning(
                            f"<y>EMBY</y>：ID验证未通过，tmdb_id: {tmdb_id}并非系列ID，判断该ID不可用")
                        tmdb_id = None
                except (AppError.Exception, Exception) as e:
                    logger.opt(colors=True).warning(
                        f"<y>EMBY</y>：ID验证异常：{e},判断该ID不可信")
                    tmdb_id = None
            # 如果验证通过，直接返回
            if tmdb_id:
                logger.opt(colors=True).info(
                    f"<g>EMBY</g>：ID验证通过，tmdb_id: {tmdb_id}")
                return tmdb_id, imdb_id, tvdb_id
            # 如果未获取到tmdb_id，则通过异步请求获取
            try:
                tasks = []
                tasks.append(TmdbRequest.get_id_from_online(
                    imdb_id, "imdb_id"))
                tasks.append(TmdbRequest.get_id_from_online(
                    tvdb_id, "tvdb_id"))
                imdb_res, tvdb_res = await asyncio.gather(*tasks, return_exceptions=True)
                if all(isinstance(res, BaseException) for res in [imdb_res, tvdb_res]):
                    logger.opt(colors=True).warning(
                        "<y>TMDB</y>：请求均失败，返回空ID")
                    return None, imdb_id, tvdb_id
                if not isinstance(imdb_res, BaseException):
                    tmdb_id = self._get_id_from_tmdb_response(imdb_res)
                    if tmdb_id:
                        logger.opt(colors=True).info(
                            f"<g>EMBY</g>：成功从IMDB获取到tmdb_id: {tmdb_id}")
                        return tmdb_id, imdb_id, tvdb_id
                if not isinstance(tvdb_res, BaseException):
                    tmdb_id = self._get_id_from_tmdb_response(tvdb_res)
                    if tmdb_id:
                        logger.opt(colors=True).info(
                            f"<g>EMBY</g>：成功从TVDB获取到tmdb_id: {tmdb_id}")
                        return tmdb_id, imdb_id, tvdb_id
                logger.opt(colors=True).info(
                    "<y>TMDB</y>：所有请求均未获取到TMDB ID，将返回空ID")
                return None, imdb_id, tvdb_id
            except (AppError.Exception, Exception):
                raise

        def extract_series_id(self, item_type, item) -> Any | None:
            """提取Series ID"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return item.get("Id")
            elif item_type == "Episode":
                return item.get("SeriesId")
            else:
                return None

        def extract_season_id(self, item_type, item) -> Any | None:
            """提取Season ID"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return None
            elif item_type == "Episode":
                return item.get("ParentId")
            else:
                return None

        def extract_episode_id(self, item_type, item) -> Any | None:
            """提取Episode ID"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return None
            elif item_type == "Episode":
                return item.get("Id")
            else:
                return None

        def extract_series_tag(self, item_type, item) -> Any | None:
            """提取Series Tag"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return (item.get('ImageTags') or {}).get("Primary")
            elif item_type == "Episode":
                return item.get("SeriesPrimaryImageTag")
            else:
                return None

        # 暂时返回None
        def extract_season_tag(self, item_type, item) -> None:
            """提取Season Tag"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return None
            elif item_type == "Episode":
                return None
            else:
                return None

        def extract_episode_tag(self, item_type, item) -> None:
            """提取Episode Tag"""
            if not item:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item 字段")
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                return None
            elif item_type == "Episode":
                return (item.get('ImageTags') or {}).get("Primary")
            else:
                return None

        def extract_server_id(self) -> str | None:
            """提取服务器ID"""
            server = self.data.get("Server")
            if not server:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Server 字段")
            return server.get("Id")

        def extract_server_name(self) -> str | None:
            """提取服务器名称"""
            server = self.data.get("Server")
            if not server:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Server 字段")
            return server.get("Name")

        def extract_merged_episode(self, item_type) -> int | None:
            """提取合并推送集数"""
            if not item_type:
                raise AppError.Exception(
                    AppError.ParamNotFound, "参数缺失！缺少 Item Type 字段")
            if item_type == "Series":
                logger.opt(colors=True).info(
                    "<g>EMBY</g> 正在提取合并集数信息")
                webhook_title = self.data.get("Title")
                if not webhook_title:
                    raise AppError.Exception(
                        AppError.ParamNotFound, "参数缺失！缺少 Title 字段")
                # 尝试从标题中提取集数
                match = re.search(r'已添加了\s*(\d+)\s*项', webhook_title)
                if match:
                    return int(match.group(1))
                else:
                    logger.opt(colors=True).info(
                        "<y>EMBY</y> 未能从标题中提取合并集数，将返回None")
                    return None
            elif item_type == "Episode":
                return None
            else:
                return None

        def extract_raw_data(self) -> str:
            """提取原始数据"""
            return json.dumps(self.data, ensure_ascii=False)

        def _get_id_from_tmdb_response(self, response: str | None) -> str | None:
            """从TMDB响应中获取ID"""
            tmdb_id = None  # 初始化
            if not response:
                logger.opt(colors=True).warning(
                    "<y>TMDB</y> 未获取到返回数据，将返回空ID")
                return None
            try:
                response_json = json.loads(response)
                if not response_json:
                    return None
                # 解析数据
                tv_results = response_json.get("tv_results", [])
                tv_episode_results = response_json.get(
                    "tv_episode_results", [])
                # 优先使用tv_results
                if tv_results and tv_results[0].get("show_id"):
                    tmdb_id = tv_results[0]["show_id"]  # 直接访问，已确认存在
                # 次选tv_episode_results
                elif tv_episode_results and tv_episode_results[0].get("show_id"):
                    tmdb_id = tv_episode_results[0]["show_id"]
                # 如果都没有，则返回None
                if not tmdb_id:
                    return None
                return tmdb_id
            except Exception as e:
                raise AppError.Exception(
                    AppError.UnknownError, f"TMDB响应解析异常：{e}")

        async def _verify_id_from_response(self, tmdb_id: int) -> bool:
            """验证ID是否有效"""
            if not tmdb_id:
                logger.opt(colors=True).warning(
                    "<y>TMDB</y> ID为空，无法验证ID")
                return False
            try:
                response = await TmdbRequest.tmdb_id_verification(tmdb_id)
                if not response:
                    logger.opt(colors=True).warning(
                        "<y>TMDB</y> 未获取到返回数据,失败")
                    return False
                response_json = json.loads(response)
                if not response_json:
                    logger.opt(colors=True).warning(
                        "<y>TMDB</y> 响应数据为空，失败")
                    return False
                if response_json.get("status_code") == 34:
                    logger.opt(colors=True).warning(
                        f"<y>TMDB</y> ID {tmdb_id} status_code is 34，失败")
                    return False
                if response_json.get("success") is False:
                    logger.opt(colors=True).warning(
                        f"<y>TMDB</y> ID {tmdb_id} success is false，失败")
                    return False
                return True
            except aiohttp.ClientResponseError as e:
                if e.status == 404:  # 可以直接访问 status为404，已确认不存在
                    logger.opt(colors=True).warning(
                        f"<y>TMDB</y> ID {tmdb_id} 不存在，失败")
                    return False
                else:
                    raise AppError.Exception(
                        AppError.RequestError, f"TMDB请求异常：{e}")
            except (AppError.Exception, Exception) as e:
                raise AppError.Exception(
                    AppError.UnknownError, f"TMDB ID验证异常：{e}")

    def _enable_anime_process(self):
        """
        可选项，启用Anime数据处理
        这里可以根据实际需求决定是否启用Anime数据处理
        """
        return True
