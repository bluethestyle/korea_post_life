# 글꼴 고지 (NOTICE)

이 폴더의 woff2 파일은 시안(`site/proto/`)에 심는 글꼴입니다. 모두 SIL Open Font License 1.1(https://openfontlicense.org)로 배포되는 글꼴이고, 쓰는 글자만 남기도록 줄였습니다(서브셋). 그에 따라 글꼴 파일 안의 글꼴 이름을 `PL Sub <원래 이름의 머리글자> <굵기>` 꼴로 바꿨고, 원래의 저작권과 라이선스 표기는 파일 안에 그대로 남겼습니다. 라이선스 전문은 각 줄 끝의 주소에 있습니다.

- Michroma: Copyright 2011 The Michroma Project Authors (https://github.com/googlefonts/Michroma-font). SIL Open Font License 1.1. https://raw.githubusercontent.com/google/fonts/main/ofl/michroma/OFL.txt
- Saira (Semi Expanded, 폭 112.5): Copyright 2020 The Saira Project Authors (https://github.com/Omnibus-Type/Saira). SIL Open Font License 1.1. https://raw.githubusercontent.com/google/fonts/main/ofl/saira/OFL.txt
- SUIT: Copyright (c) 2022, SUNN (http://sun.fo/suit), with Reserved Font Name SUIT. SIL Open Font License 1.1. https://raw.githubusercontent.com/sun-typeface/SUIT/main/LICENSE
- Saira (Semi Condensed, 폭 87.5): Copyright 2020 The Saira Project Authors (https://github.com/Omnibus-Type/Saira). SIL Open Font License 1.1. https://raw.githubusercontent.com/google/fonts/main/ofl/saira/OFL.txt

관계 그래프 화면(`site/proto/graph2.html`)에 심는 `fonts_graph2.css`의 글꼴은 아래와 같다. 모두 SIL Open Font License 1.1이고 쓰는 글자만 남긴 서브셋인데, 위의 woff2와 달리 글꼴 파일 안의 이름을 바꾸지 않았다(원래 이름과 저작권 표기가 그대로 있다).

- IBM Plex Sans KR (Regular 400, SemiBold 600, Bold 700): Copyright 2018 IBM Corp. SIL Open Font License 1.1. https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexsanskr/OFL.txt
- Chakra Petch (Medium 500, Bold 700): Copyright 2018 The Chakra Petch Project Authors (https://github.com/m4rc1e/Chakra-Petch.git). SIL Open Font License 1.1. https://raw.githubusercontent.com/google/fonts/main/ofl/chakrapetch/OFL.txt
- Michroma (Regular 400, 영문과 숫자만): 위의 Michroma와 같다.

`fonts_v4.css`는 SUIT 400, 600과 Saira Semi Condensed 400, 600을 base64로 담은 @font-face 묶음이고 분석 화면(`site/proto/console4.html`)에 심는다. 발표 덱(`site/deck/index.html`)에는 그 가운데 SUIT(PLKo, 400과 600)만 심는다(`proto_src/deck/build.py`).
