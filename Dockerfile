FROM python:3.11.12-slim-bookworm

# install required packages (ARM64-compatible: uses chromium instead of google-chrome)
RUN apt-get update && apt-get install -y \
    wget gnupg \
    python3-tk python3-dev \
    chromium chromium-driver \
    libnss3 libxss1 libatk-bridge2.0-0 libgtk-3-0 \
    libdrm2 libxcomposite1 libxrandr2 libgbm1 libasound2 \
    fonts-liberation \
  && rm -rf /var/lib/apt/lists/*

# set the working directory to /src
WORKDIR /src

# upgrade pip
RUN python -m pip install --no-cache-dir --upgrade pip

# install dependencies
COPY ./requirements.txt /src
RUN python -m pip install --no-cache-dir -r requirements.txt

# copy the current directory contents into the image
COPY . /src

# set display port – the host XRDP runs on :10, but inside the container
# the entrypoint can override this with its own Xvfb if needed.
ENV DISPLAY=:10

RUN python3 - <<EOF
from undetected_chromedriver.patcher import Patcher
p = Patcher()
p.auto()
EOF

ENTRYPOINT ["python"]
