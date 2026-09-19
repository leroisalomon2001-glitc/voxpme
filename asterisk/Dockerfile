# =============================================================================
# VoxPME — Asterisk 20 compilé from source, ARA/ODBC, AGI Python embarqué
# =============================================================================

# ---------- Stage 1 : builder -----------------------------------------------
FROM debian:12-slim AS builder

RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4\
    && echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries \
    && echo 'Acquire::http::Timeout "60";' >> /etc/apt/apt.conf.d/80retries

ARG ASTERISK_VERSION=20

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential wget subversion
RUN apt-get install -y --no-install-recommends libnewt-dev libssl-dev libncurses5-dev
RUN apt-get install -y --no-install-recommends libxml2-dev linux-headers-generic libsqlite3-dev
RUN apt-get install -y --no-install-recommends uuid-dev libjansson-dev libedit-dev
RUN apt-get install -y --no-install-recommends unixodbc-dev pkg-config ca-certificates
RUN apt-get install -y --no-install-recommends git libsrtp2-dev
RUN rm -rf /var/lib/apt/lists/*



# WORKDIR ne fait pas d'expansion de glob (un éventuel "*" n'y serait pas
# interprété) : on renomme donc le dossier extrait vers un nom fixe et
# prévisible ci-dessous, sur lequel le WORKDIR suivant peut pointer sans
# ambiguïté.
WORKDIR /usr/src
RUN wget -q https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-${ASTERISK_VERSION}-current.tar.gz \
    && tar zxf asterisk-${ASTERISK_VERSION}-current.tar.gz \
    && rm asterisk-${ASTERISK_VERSION}-current.tar.gz \
    && mv asterisk-${ASTERISK_VERSION}* asterisk-src

WORKDIR /usr/src/asterisk-src

# Dépendances additionnelles (pjproject inclus pour PJSIP)
# Le cache apt a été purgé après l'installation précédente (rm -rf
# /var/lib/apt/lists/*, pour garder l'étape allégée) — install_prereq a
# besoin de ce cache pour installer ses propres dépendances (aptitude,
# etc.), donc on le régénère juste avant, puis on le purge à nouveau après.
RUN apt-get update \
    && contrib/scripts/install_prereq install \
    && rm -rf /var/lib/apt/lists/*

# Config du build : ARA (ODBC), PJSIP, ARI, app_queue, cdr_adaptive_odbc
RUN ./configure --with-jansson-bundled \
    && make menuselect.makeopts \
    && menuselect/menuselect \
    --enable res_odbc \
    --enable res_config_odbc \
    --enable cdr_adaptive_odbc \
    --enable res_pjsip \
    --enable res_ari \
    --enable app_queue \
    --enable res_srtp \
    menuselect.makeopts

RUN make -j"$(nproc)" && make install && make samples && make config

# ---------- Stage 2 : image finale (runtime) --------------------------------
FROM debian:12-slim

RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4\
    && echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries \
    && echo 'Acquire::http::Timeout "60";' >> /etc/apt/apt.conf.d/80retries

RUN apt-get  update && apt-get install -y --no-install-recommends \
    unixodbc odbc-postgresql gettext-base libxslt1.1 liburiparser1 libcap2 \
    libnewt0.52 libssl3 libxml2 libsqlite3-0 uuid-runtime \
    libjansson4 libedit2 libsrtp2-1  \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --break-system-packages psycopg2-binary
# gettext-base fournit envsubst, utilisé par docker-entrypoint.sh
# psycopg2-binary requis par ivr_engine.py (AGI)

# Binaires + config générée par le builder
COPY --from=builder /usr/sbin/asterisk /usr/sbin/asterisk
COPY --from=builder /usr/lib/asterisk /usr/lib/asterisk
COPY --from=builder /usr/lib/libasterisk*.so* /usr/lib/
RUN ldconfig
COPY --from=builder /var/lib/asterisk /var/lib/asterisk
COPY --from=builder /etc/asterisk /etc/asterisk
COPY --from=builder /usr/include/asterisk* /usr/include/

# Patch documentation XML : bloc "identify" mal placé sous res_pjsip_endpoint_identifier_ip
# au lieu de res_pjsip dans le core-en_US.xml généré par ce build (bug reproductible,
# cf. J17/J20 du journal) — sans ce patch, res_pjsip_endpoint_identifier_ip.so refuse de
# charger ("Cannot update type identify... no existing documentation").
COPY core-en_US.xml /var/lib/asterisk/documentation/core-en_US.xml

RUN useradd -r -d /var/lib/asterisk asterisk \
    && mkdir -p /var/run/asterisk /var/log/asterisk /var/spool/asterisk \
    && touch /etc/odbc.ini \
    && chown -R asterisk:asterisk /var/run/asterisk /var/log/asterisk \
    /var/spool/asterisk /var/lib/asterisk /etc/asterisk /etc/odbc.ini

# AGI Python (ivr_engine.py) — lancé par Asterisk lui-même en local
COPY ivr_engine.py /var/lib/asterisk/agi-bin/ivr_engine.py
RUN chmod +x /var/lib/asterisk/agi-bin/ivr_engine.py \
    && chown asterisk:asterisk /var/lib/asterisk/agi-bin/ivr_engine.py

# Config bootstrap : montée en volume dans docker-compose sur
# /etc/asterisk/bootstrap (contient ${ODBC_DSN_PASSWORD} à substituer au
# démarrage par docker-entrypoint.sh, avant de copier vers /etc/asterisk et
# /etc/odbc.ini)
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 5060/udp 5060/tcp 5061/tcp 8088/tcp 8089/tcp
# RTP : plage définie dans rtp.conf, ouverte via network_mode: host

USER asterisk
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
