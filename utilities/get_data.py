from urllib import request
from typing import Optional
from fake_useragent import UserAgent
from tqdm.auto import tqdm
from typing import Optional, Tuple


class ProgressBar(tqdm):
    def progress(
        self, block: int = 1, block_size: int = 1, total_size: Optional[int] = None
    ):
        if total_size is not None:
            self.total = total_size
        return self.update(block * block_size - self.n)


def downloader(filename: str, link: str) -> Tuple[bool, Optional[str]]:
    try:
        with ProgressBar(
            unit="B", unit_scale=True, unit_divisor=1024, miniters=1, desc=""
        ) as progress_bar:
            opener = request.build_opener()
            opener.addheaders = [("User-Agent", UserAgent().firefox)]
            request.install_opener(opener)
            request.urlretrieve(
                link, filename=filename, reporthook=progress_bar.progress, data=None
            )
            progress_bar.total = progress_bar.n
    except Exception as error:
        return False, error
    return True, None
