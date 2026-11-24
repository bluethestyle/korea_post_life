/* 시안 4 공통 실행부: 안개 바탕 위 기준축과 기둥 무대, 상단 고리 탭 줄, 읽기 영역, 눌러서 여는 전체 표 창.
   화면 문구는 아래 COPY 한 곳에서 읽고, 회사 목록과 업권, 비교 범위 교집합은 자료(sales.json, d.json)에서 읽는다. */
(function () {
  'use strict';

  const S = window.__BOOT_S || JSON.parse(document.getElementById('sales-data').textContent);
  try { delete window.__BOOT_S; } catch (e) { /* */ }
  const DD = (typeof D !== 'undefined') ? D : null;

  // ---------- 화면 문구 표(한 곳에서 관리) ----------
  const COPY = {
    appTitle: '영업 분석 콘솔',
    homeTitle: '영업 분석 요약',
    homePathRoot: '전체 요약',
    tabGraph: '관계 그래프',
    bootAria: '화면 열기 진행률',
    tabsAria: '분석 화면',
    skinDark: '다크 모드',
    skinLight: '라이트 모드',
    motionWord: '애니메이션',
    motionOn: '켬',
    motionCalm: '줄임',
    motionOff: '끔',
    condAria: '조건 줄',
    condOpenBtn: '조건 바꾸기',
    condCloseBtn: '조건 접기',
    condBasePrefix: '기준',
    condPeerPrefix: '상대',
    condPeerNone: '선택 없음',
    condNoHist: '이력 없음',
    condSurgOnly: '수술만',
    condHospOrSurg: '입원이나 수술',
    condSince5: '5년 넘음',
    condSinceUnit: '년 전',
    condGroupSeg: '지금 보는 고객군',
    condAge: '나이',
    condAgeUnit: '세',
    condSex: '성별',
    condMale: '남성',
    condFemale: '여성',
    condSince: '마지막 입원이나 수술',
    condSurgKind: '이력의 종류',
    condSurgSwitch: '입원 없이 수술만',
    condSurgDisHint: '이력이 없으면 고르지 않습니다',
    condSurgHint: '고지 질문이 수술을 묻는지에 따라 회사마다 관문이 갈립니다',
    condGroupBase: '기준과 비교 상대',
    condBase: '기준 종형',
    condPeers: '비교 상대',
    condPeersHint: '비교 범위에 맞춰 걸러집니다',
    condRenewal: '갱신 유형',
    condRenewalHint: '고객군과 관문 지도에 씁니다',
    condRenAll: '전체',
    condRenRenew: '갱신',
    condRenNon: '비갱신',

    scopeBtn: '범위',
    peerBtnTpl: '비교: {s}',
    peerTitle: '비교 범위',
    peerAll: '전체',
    peerLife: '생명보험만',
    peerNonLife: '손해보험만',
    peerCustom: '직접 고른 회사',
    peerLifeGroup: '생명보험',
    peerNonLifeGroup: '손해보험',
    peerCustomShortTpl: '선택 {n}곳',
    peerEmptyHint: '선택한 비교 범위에 해당하는 상대 회사가 없습니다.',
    peerRestTpl: '{first} 외 {rest}곳',
    peerEtcTpl: '{names} 등 {total}곳',
    fullScopeBadge: '전체 기준',
    fullScopeHint: '자료의 문장과 집계는 전체 비교 상대 기준으로 작성한 값입니다',
    sameCountSuffix: '개',
    scopeAria: '범위 띠',
    scopeTitle: '범위 띠',
    scopeVsAria: '대',
    scopeDiffStruct: '구조 다름',
    scopeDiffStructHint: '갱신이나 환급 구조가 다름',
    scopePairTpl: '공통 담보 {total}쌍 가운데 검토 대기로 뺀 쌍 {wait}',
    scopeNowSeg: '지금 고객군',
    scopeOurRep: '우리 대표 종형',
    scopeSwitchBaseTpl: '기준 종형을 {target} 바꾸기',
    scopeClosedWhy: '닫힌 사유',
    scopeNoData: '자료 없음',

    pathAria: '현재 층 경로',
    zoneLeftAria: '분류',
    zoneCenterAria: '단위 도형',
    evAria: '고른 것의 상세',
    evKickerDefault: '화면 결론',
    evKickerPick: '상세와 근거',
    evPanelName: '상세와 근거',
    evCloseAria: '상세 닫기',
    evMoreBtn: '아래로 스크롤해 더 보기',
    zlSecTitle: '구역 이동',
    footNoticeHead: '유의사항.',
    footDisclaimer: '상품요약서와 사업방법서 같은 공시 문서에서 뽑은 값으로 계산했고, 판매 시책, 수수료, 손해율, 인수 판정은 다루지 않습니다.',
    footAsof: '자료 기준',
    footFontHead: '글꼴 라이선스',

    scopeAll: '전체 고객군',
    scopeAllHint: '기준 종형과 조건을 바꿔도 그대로인 값',
    scopeBase: '선택 종형',
    scopeBaseHint: '기준 종형을 바꾸면 바뀌는 값',
    scopeNow: '지금 조건',
    scopeNowHint: '나이, 성별, 이력을 바꾸면 바뀌는 값',

    vdBetter: '우체국 나음',
    vdOnly: '우체국에만 있음',
    vdWorse: '우체국 못함',
    vdSame: '같음',
    vdDiff: '우열을 매기지 않음',
    vdNone: '우체국에 없음',
    vdUnknown: '모름',
    flagDefault: '사업방법서 원문 확인 필요',
    flagShort: '원문 확인',

    actBack: '뒤로',
    actModeText: '문장으로 보기',
    actModeTable: '표로 보기',
    actModeShape: '도형으로 보기',
    actCopySum: '요약 복사',
    legendBtn: '범례',
    legendCloseAria: '창 닫기',
    modalCloseBtn: '닫기',
    helpSuffixAria: ' 뜻 보기',
    legendVerdictTitle: '판정과 기둥 범례',
    lgBetter: '같은 담보를 견줘 우체국 조건이 나은 것(금색)',
    lgOnly: '견준 상대에는 없고 우체국에만 있는 담보나 우리만 열리는 고객군(금색 이중선)',
    lgWorse: '같은 담보를 견줘 우체국 조건이 못하거나 우리만 닫힌 곳(먹색 채움)',
    lgSame: '조건이 같은 것(중립)',
    lgDiff: '지급 형태나 판매 구성이 달라 우열을 매기지 않은 것(중립)',
    lgNone: '상대에는 있고 우체국에는 없는 담보나 닫힌 구간(점선 윤곽)',
    lgUnknown: '검토 대기이거나 자료가 아직 없는 구간(빗금)',
    lgFlag: '화면에 옮긴 값이 사업방법서 원문과 같은지 사람이 확인해야 합니다',
    lgSel: '지금 고른 항목. 읽기 영역으로 1px 선이 이어집니다',
    lgScopeAll: '기준 종형과 조건을 바꿔도 그대로인 값입니다.',
    lgScopeBase: '기준 종형을 바꾸면 다시 계산하는 값입니다.',
    lgScopeNow: '조건 줄의 나이, 성별, 이력을 따라 바뀌는 값입니다.',

    termScopeTitle: '범위 띠',
    termScopeBody: '위쪽 줄은 지금 고른 기준 종형과 맞붙는 상대 상품, 공통 담보 쌍의 수를 보여 줍니다. 아래쪽 줄은 조건 줄의 나이, 성별, 이력이 고객군 지도에서 어느 관문 칸에 해당하는지 보여 줍니다.',
    termEvTitle: '읽기 영역',
    termEvBody: '무대에서 도형을 고르면 그 단위의 이름, 판정, 문장, 관계 식, 원문 문서 쪽 번호를 이 영역에 보여 줍니다. 아무것도 고르지 않았을 때는 면 없이 지금 화면의 결론 한 문장만 보여 줍니다.',
    termBaseTitle: '기준 종형과 선택 종형',
    termBaseBody: '기준 종형은 조건 줄에서 고른 우체국 상품 종형이며, 비교 상대는 그 종형의 심사 유형과 갱신 구조에 맞춰 정해집니다. 선택 종형 배지가 붙은 숫자와 문장은 이 기준 종형을 바꿀 때 함께 다시 계산하는 값입니다.',
    termJourneyTitle: '치료 여정 격자',
    termJourneyBody: '암, 뇌혈관, 심장 같은 보장 대분류와 치료 단계가 만나는 칸마다 회사별 표준담보 수를 견준 표입니다. 빈 단계나 담보 수 차이를 한눈에 살피는 용도이며, 조건의 우열은 담보 비교표에서 따집니다.',
    termCautionTitle: '단정 주의와 검토 대기',
    termCautionBody: '단정 주의는 상대가 조건이 다른 특약을 함께 팔거나 지급 형태가 달라 우열 문장을 내지 않고 사실만 적은 담보입니다. 검토 대기는 급부의 표준담보 매핑(매핑 대기)이나 추출한 급부 줄(작업 로그 대기)을 아직 사람이 확인하지 않아 비교 계산에서 뺀 쌍입니다.',

    noteHeadMap: '지도가 보는 범위',
    noteHeadSimp: '간편심사의 대상',
    noteHeadSurg: "'수술만' 행의 뜻",
    noteHeadGen: '일반심사 규칙',
    notesTitle: '일러두기',
    notesAriaSuffix: ' 주석',
    notesSrcPrefix: '출처: ',

    whyNoAgeTpl: '나이 자료 없음: {org}의 가입나이 자료가 아직 들어오지 않았습니다',
    whyNoQstTpl: '질문 자료 없음: {org}의 고지 질문 자료가 아직 들어오지 않았습니다',
    whySegAgeTpl: '나이 자료 없음: 고객군 지도는 {lo}~{hi}세만 계산했습니다',
    whySegRow: '이력 자료 없음: 이 이력의 칸이 지도에 없습니다',
    whySegSexTpl: '{sex} 지도 자료 없음: 고객군 지도는 {mapSex} 기준으로만 계산해 {mapSex} 칸을 보입니다',
    flowAgeNoteTpl: '관문 흐름 통과 수는 지도 칸의 세부나이({age}세, {sex}) 기준입니다.',
    flowAgeNoteNoHistTpl: '관문 흐름 통과 수는 이력 없는 고객의 세부나이({age}세, {sex}) 기준입니다.',
    docFallback: '문서',
    pageSuffix: '쪽',
    pageMissingSuffix: ': 쪽 번호 자료 없음',
    pageWhy: '쪽 번호 자료 없음: 고지 질문과 가입나이는 사업방법서에서 읽은 값이고, 사본에 그 쪽 번호가 들어 있지 않습니다. 원문의 해당 조항을 찾아 대조합니다',
    sameOnlyOneTpl: '{org}만 값이 있음',
    sameNone: '값이 있는 회사 없음',
    sameDiff: '회사마다 다름',
    sameAllTpl: '{n} 회사 같음',
    sameHaveTpl: '값이 있는 {n} 회사 같음',
    wordTwo: '두',
    wordThree: '세',

    copyOk: '복사했습니다',
    copyFail: '복사하지 못했습니다. 브라우저가 막았습니다',
    copyRowsOkTpl: '복사했습니다: {n}줄. 엑셀이나 한글 문서에 붙여 넣으면 됩니다',
    scopeLineTpl: '범위: 기준 종형 {base} / 비교 상대 {peers} / 지금 고객군 {seg} / 자료 기준 {asof} / {notice}',
    printMark: '내부 교육·비교 참고용(대외 배포 금지)',
    tabMissing: '이 화면의 파일이 아직 없습니다.',
    tabErrorPrefix: '이 화면을 그리다 멈췄습니다: ',
    chevPrevSuffix: ' 앞 값',
    chevNextSuffix: ' 다음 값',
    stepDecSuffix: ' 하나 줄이기',
    stepIncSuffix: ' 하나 늘리기',

    // 첫 화면(전체 요약)과 상단 고리 탭 문구
    homeListHeadTpl: '전체 결론 {n}줄',
    homeListHint: '줄을 누르면 해당 화면으로 들어갑니다',
    homeRevBadgeTpl: '개정 {n}',
    briefRowGa: '고객군 지형',
    briefRowNa: '개정과 시장',
    briefRowDa: '가입 관문과 한도',
    briefRowRa: '담보 포지션',
    briefRowMa: '영업 인사이트',
    briefCopyTitle: '브리핑 분석 요약',
    briefCopyCols: '줄,구역,범위,문장,갈 곳',
    briefOffCondTpl: '지금 조건({cond})은 대표 조건({ref})과 다릅니다. 요약 문장은 대표 조건 기준입니다.',
    briefLimitOutTpl: '지금 조건 {who}: {kind}의 가입나이({lo}~{hi}세) 밖입니다.',
    briefLimitInTpl: '지금 조건 {who}: 주계약 최대 가입금액 {max}만원({lo}~{hi}세 구간{extra}).',
    briefLimitPend: ', 검토 대기',
    briefLimitSameSex: ', 남녀 같음',
    homeLegendTitle: '첫 화면 기준축과 기둥 읽는 법',
    homeLgGold: '금색 기둥(이중 상단선): 우체국 조건이 나은 담보이거나 우리 간편만 열리는 고객군',
    homeLgWorse: '먹색 채움 기둥: 우체국 조건이 못하거나 우리 간편은 닫히고 상대는 열리는 고객군',
    homeLgNeutral: '중립 기둥: 함께 열리는 고객군, 조건이 같거나 우열을 매기지 않은 담보',
    homeLgOutline: '일부 채움 기둥: 바깥 윤곽은 전체 상대 수, 안쪽 채움은 통과한 상대 수',
    homeLgEmpty: '점선 윤곽과 빗금: 닫힌 구간, 우체국 미보유 담보, 검토 대기 및 자료 없음',
    homeLgRed: '빨강 마름모와 세로선: 지금 올리거나 고른 묶음',

    // 고객군과 시장(tab2) 문구
    mkRenLabel: '갱신',
    mkRenAria: '고객군 지도의 갱신 유형',
    mkMaleBasis: '남성 기준',
    mkGroupAll: '고객군 전체',
    mkGroupHosp: '입원',
    mkGroupSurg: '수술만',
    mkGroupRev: '개정과 시장',
    mkGroupTally: '집계와 일러두기',
    mkCenterTitle: '고객군 시간축과 고리',
    mkTimeOver5: '5년+',
    mkUnknownSym: '?',
    mkOursOpenRatioTpl: '우리 열림 {open}/{total}',
    mkPartialOnlyMark: '일부 나이만',
    mkPartialHeadTpl: '일부 나이에서만 열리는 상대 {n}곳',
    mkPartialSpanTpl: '{org} {spans}세만 열림',
    mkRevTabVar: '개정 변동',
    mkRevTabNews: '시장 소식',
    mkRevHead: '우체국 직전 개정과 견준 변동',
    mkRevCopyBtn: '표 복사',
    mkRevNonAddTpl: '개정 짝 {c}개의 수를 더하면 {sum}건입니다. 같은 담보가 여러 짝에서 바뀌면 짝마다 세므로 전체 {total}건보다 큽니다.',
    mkRevGateChg: '고지 질문이 바뀐 종형',
    mkRevAgeChg: '가입나이가 바뀐 종형',
    mkRevNone: '없음',
    mkRevNote: '짝마다 직전 개정 종형과 같은 담보를 견줘 신설, 변경, 종료로 셉니다. 직전 개정 종형은 판매를 마쳐 견준 상품 목록에 이름이 없습니다.',
    mkRevCols: '담보,종류,달라진 항목,종형',
    mkRevNew: '신설',
    mkRevChg: '변경',
    mkRevEnd: '종료',
    mkNewsHead: '시장 소식',
    mkNewsQuoteTag: '인용',
    mkNewsConnTpl: '표준담보에 이어진 소식 {n}건.',
    mkNewsNoConn: ' 이어진 담보가 없어 대응 문장을 달지 않습니다.',
    mkNewsNonAddNote: '시장 소식 건수는 개정 변동 담보 수와 단위가 달라 더하지 않습니다.',
    mkNewsLinkedTpl: ', 표준담보 {n}개에 이어짐',
    mkNewsUnlinked: ', 표준담보에 이어지지 않음',
    mkNewsWarnTpl: '주의 표현 {w}',
    mkNewsWarnHint: '화면 문장에 쓰지 않는 말이 보도 요약에 들어 있습니다',
    mkTallyHead: '라벨별 칸 수와 자료 점검',
    mkTallyCol1: '주 라벨',
    mkTallyCol2: '칸 수',
    mkTallyCopyBtn: '집계 복사',
    mkCellsCopyBtn: '칸 목록 복사',
    mkClosedUnit: '칸',
    mkClosedNoteTpl: '우리 간편이 닫힌 칸 {cells}칸의 사유는 {why}입니다.',
    mkClosedNonAddTpl: '한 칸에 사유 둘이 함께 들 수 있어 사유별 칸 수를 더하면 {sum}칸으로 {cells}칸보다 큽니다.',
    mkClosedZero: '우리 간편이 닫힌 칸이 없습니다.',
    mkGapItemTpl: '{org} 자료 없음 표지 {n}칸. {why}',
    mkStaticNote: '칸의 수는 기준 종형과 조건을 바꿔도 그대로입니다. 갱신 유형 거르개를 바꾸면 그 유형의 종형만으로 다시 센 지도로 바뀝니다.',
    mkLegendTitle: '고객군 시간축과 고리 읽는 법',
    mkLgWorse: '먹색 채움 원(흰 숫자): 우리 간편은 닫히고 열린 상대가 있는 고객군',
    mkLgGold: '금색 이중 고리: 우리 간편만 열리는 고객군(열린 상대 0곳)',
    mkLgBoth: '짙은 선 고리: 우리 간편과 상대가 함께 열리는 고객군',
    mkLgAllClosed: '옅은 회색 고리: 우리와 상대 모두 간편심사가 닫힌 고객군',
    mkLgDash: '점선 고리와 빗금 트랙: 가입나이나 고지 질문 자료가 아직 없는 구간',
    mkLgArc: '바깥 호: 실선은 확정 열림, 반굵기 실선은 일부 나이만 열림, 점선은 관문만 열림',
    mkLgAxis: '마디 사이 선분: 우리 간편이 이어서 열리면 2px 실선, 닫히면 1px 점선(전환 자리에 12px 눈금)',
    mkLgRed: '빨강 원과 네 귀 사선: 지금 고른 고객군. 오른쪽 읽기 영역으로 1px 선이 이어집니다',
    mkEvKickerCell: '고객군 상세',
    mkEvNowTag: '지금 조건',
    mkEvOursHead: '우리 종형 상태',
    mkEvOursRep: '우리 대표 종형',
    mkEvOpenPeersHeadTpl: '열린 상대 {open}/{total}곳',
    mkEvOpenAllSummaryTpl: '열린 상대 {n}곳 모두 보기',
    mkEvOrgsSummaryTpl: '회사별 상태 {n}곳 모두 보기',
    mkEvClosedSummaryTpl: '닫힘 및 심사 확인 상대 {n}곳 보기',
    mkCatWait: '검토 대기',
    mkEvOpenVarCntTpl: '열린 종형 {n}개: {list}',
    mkEvOpenVarNone: '열린 종형 없음',
    mkEvGatePtsTpl: '관문 포인트와 근거 ({n}건)',
    mkEvGatePtsNone: '이 고객군에서 나온 관문 차이가 없습니다.',
    mkEvRepAndCnts: '대표 종형과 분류별 인사이트 수',
    mkEvPeerRep: '상대 대표 종형',
    mkEvSameCond: '지금 조건이 이미 이 고객군입니다.',
    mkEvWillChangeTpl: '누르면 조건 줄이 {target} 바뀝니다.',
    mkEvApplyBtn: '이 고객군으로 조건 바꾸기',
    mkEvChangedToastTpl: '조건을 바꿨습니다: {sum}',
    mkEvRuleNote: '관문 상태는 사업방법서의 고지 질문과 가입나이로 계산했습니다. 칸에 우열을 매기지 않습니다.',
    mkEvGraphBtn: '관계 그래프에서 보기',
    mkEvRevKicker: '개정 변동 상세',
    mkEvRevVars: '해당 종형',
    mkEvRevStdNoteTpl: '{target} 이어 견줬습니다. 공시 문서(상품요약서와 사업방법서)의 개정 전후를 견준 값입니다.',
    mkEvRevRawNote: '표준담보에 이어지지 않은 급부라 급부 이름으로 견줬습니다. 공시 문서의 개정 전후를 견준 값입니다.',
    mkEvNewsKickerTpl: '시장 소식 {week}',
    mkEvNewsSrcHead: '출처',
    mkEvNewsOrg: '회사',
    mkEvNewsCat: '분류',
    mkEvNewsDate: '발표일',
    mkEvNewsMedia: '매체',
    mkEvNewsUrlNote: '주소는 글자로만 둡니다. 이 화면은 바깥으로 요청하지 않습니다.',
    mkEvNewsStdHead: '표준담보와 주의 표현',
    mkEvNewsStdLinkedTpl: '표준담보 {list}에 이어졌습니다.',
    mkEvNewsWarnBodyTpl: '보도 요약에 "{list}" 같은 말이 들어 있습니다. 화면 문장에는 쓰지 않는 말이라 인용한 그대로 두고 표지만 붙였습니다.',
    mkMissingSegWhyTpl: '지금 조건의 칸이 이 지도에 없습니다. {why}',

    // 관계 지도(graph) 문구
    grLeftHead: '보는 틀',
    grKindOrg: '회사',
    grKindVar: '종형',
    grKindStd: '표준담보',
    grKindPt: '영업 포인트',
    grKindNews: '소식',
    grCenterDesc: '소식, 회사, 종형, 특약, 급부, 표준담보, 보장분야의 일곱 열을 한 홉씩 펼쳐 비교합니다.',
    grEvTitle: '관계 그래프',
    grEvBodyTpl: '노드를 눌러 옆 열의 이웃을 펼치거나, 연결선을 눌러 검토상태와 급부역할 같은 관계 속성을 확인합니다.',
    grLegendTitle: '관계 그래프 도형과 선 안내',
    grLgNode: '직각 칸: 회사(먹색 면), 종형(2px 윤곽), 특약(1px 윤곽), 급부(요약), 표준담보(이중 윤곽, 비교 종형에 연결이 없는 담보는 옅은 단선 윤곽), 보장분야(넓은 띠), 소식(날짜). 우체국은 왼쪽 3px 변',
    grLgEdge: '연결선: 판매와 포함(실선), 해당(승인 및 수정은 굵은 실선), 속함(가는 선), 관계(이중선), 일으킴(점선)',
  };

  function cp(key, vars) {
    let s = key in COPY ? COPY[key] : key;
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll('{' + k + '}', String(v == null ? '' : v));
    return s;
  }

  const SCREEN_IDS = ['market', 'gate', 'cover', 'insight', 'graph'];
  const TAB_IDS = ['brief'].concat(SCREEN_IDS);
  const TAB_NAME = {
    brief: cp('homeTitle'),
    market: S['탭'][1],
    gate: S['탭'][2],
    cover: S['탭'][3],
    insight: S['탭'][4],
    graph: cp('tabGraph'),
  };
  const TAB_BY_NAME = {
    [S['탭'][0]]: 'brief',
    [cp('homeTitle')]: 'brief',
    [cp('homePathRoot')]: 'brief',
    [S['탭'][1]]: 'market',
    [S['탭'][2]]: 'gate',
    [S['탭'][3]]: 'cover',
    [S['탭'][4]]: 'insight',
    '관계 지도': 'graph',
    [cp('tabGraph')]: 'graph',
  };
  const TAB_BRIEF_KEY = { market: '가', gate: '다', cover: '라', insight: '마' };

  // ---------- 회사 목록과 업권 동적 수집 ----------
  const ORG_NAME = {}, ORG_SECTOR = {};
  const orgSeen = new Set(['EPOST']);
  const ORG_ORDER = ['EPOST'];
  function inferSector(code, nm, sec) {
    const raw = String(sec || '');
    if (raw.includes('손해') || raw.includes('화재')) return 'nonlife';
    if (raw.includes('생명')) return 'life';
    const label = String(nm || code || '');
    if (/화재|손해|해상/.test(label)) return 'nonlife';
    return 'life';
  }
  function registerOrg(code, nm, sec) {
    if (!code) return;
    if (nm && !ORG_NAME[code]) ORG_NAME[code] = nm;
    if (sec) ORG_SECTOR[code] = inferSector(code, nm || ORG_NAME[code], sec);
    else if (!ORG_SECTOR[code] && code !== 'EPOST') ORG_SECTOR[code] = inferSector(code, nm || ORG_NAME[code], '');
    if (!orgSeen.has(code)) { orgSeen.add(code); ORG_ORDER.push(code); }
  }
  if (S['회사'] && typeof S['회사'] === 'object') {
    for (const [code, info] of Object.entries(S['회사'])) {
      if (info && typeof info === 'object') registerOrg(code, info['이름'] || info.name, info['업권'] || info['분류'] || info.sector);
    }
  }
  for (const v of Object.values(S['종형'] || {})) {
    registerOrg(v['기관코드'], v['회사'], v['업권'] || v['기관분류']);
  }
  if (DD && Array.isArray(DD.orgs)) {
    for (const o of DD.orgs) registerOrg(o.code, o.name || o.short, o['업권'] || o.sector);
  }
  for (const m of Object.values(S['지도'] || {})) {
    for (const row of (m && m['칸']) || []) {
      for (const cell of row || []) {
        for (const code of Object.keys((cell && cell['회사']) || {})) registerOrg(code, ORG_NAME[code], '');
      }
    }
  }
  const ORG_SHORT = { EPOST: '우체국' };
  for (const code of ORG_ORDER) {
    if (code !== 'EPOST') ORG_SHORT[code] = ORG_NAME[code] || code;
  }
  if (DD && Array.isArray(DD.orgs)) for (const o of DD.orgs) if (o.code && o.short) ORG_SHORT[o.code] = o.short;
  if (S['회사'] && typeof S['회사'] === 'object') {
    for (const [code, info] of Object.entries(S['회사'])) {
      if (info && (info['짧은이름'] || info.short)) ORG_SHORT[code] = info['짧은이름'] || info.short;
    }
  }
  const PEER_ORGS = ORG_ORDER.filter(o => o !== 'EPOST');
  const orgSector = code => (code === 'EPOST' ? 'ours' : (ORG_SECTOR[code] || inferSector(code, ORG_SHORT[code], '')));
  const BASES = S['기준종형'];
  const MAP_KEY = { null: COPY.condRenAll, '갱신': COPY.condRenRenew, '비갱신': COPY.condRenNon };
  const REF = S['기준조건'];

  // ---------- 작은 도구 ----------
  const $ = (q, r = document) => r.querySelector(q);
  const $$ = (q, r = document) => Array.from(r.querySelectorAll(q));
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  const fmt = n => (n == null || n === '' ? '' : (typeof n === 'number' ? n.toLocaleString('ko-KR') : String(n)));
  const firstSentence = s => (String(s == null ? '' : s).trim().split(/(?<=\.)\s+/)[0] || '');
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* */ } },
  };
  const LS_SKIN = 'postlife-c4-skin', LS_MOTION = 'postlife-c4-motion';

  // ---------- 글 도우미 ----------
  const CLOSE = { ')': '(', ']': '[', '}': '{' };
  function stemOf(word) {
    let s = String(word == null ? '' : word).trimEnd();
    for (let guard = 0; guard < 8; guard++) {
      s = s.replace(/[\s'"’”」』]+$/, '');
      const cl = s[s.length - 1];
      if (!(cl in CLOSE)) break;
      let depth = 0, i = s.length - 1;
      for (; i >= 0; i--) { if (s[i] === cl) depth++; else if (s[i] === CLOSE[cl] && --depth === 0) break; }
      if (i <= 0) { s = s.replace(/[)\]}\s]+$/, ''); break; }
      s = s.slice(0, i).trimEnd();
    }
    return s;
  }
  function hasFinal(word) {
    const s = stemOf(word);
    if (!s) return false;
    const c = s[s.length - 1], code = c.charCodeAt(0);
    if (code >= 0xAC00 && code <= 0xD7A3) return (code - 0xAC00) % 28 !== 0;
    if (/[0-9]/.test(c)) return '013678'.includes(c);
    if (/[A-Za-z]/.test(c)) return 'LMNRlmnr'.includes(c);
    return false;
  }
  function rieulFinal(word) {
    const s = stemOf(word);
    const c = s[s.length - 1]; if (!c) return false;
    const code = c.charCodeAt(0);
    if (code >= 0xAC00 && code <= 0xD7A3) return (code - 0xAC00) % 28 === 8;
    return c === '1' || c === '7' || c === '8' || /[lL]/.test(c);
  }
  const JOSA = { '은': ['은', '는'], '는': ['은', '는'], '이': ['이', '가'], '가': ['이', '가'], '을': ['을', '를'], '를': ['을', '를'],
    '과': ['과', '와'], '와': ['과', '와'], '이나': ['이나', '나'], '나': ['이나', '나'], '이며': ['이며', '며'], '이고': ['이고', '고'],
    '이다': ['이다', '다'], '이에요': ['이에요', '예요'], '아': ['아', '야'], '으로': ['으로', '로'], '로': ['으로', '로'] };
  function josa(word, particle) {
    const p = JOSA[particle];
    if (!p) return String(word) + particle;
    if (p[0] === '으로') return String(word) + (hasFinal(word) && !rieulFinal(word) ? '으로' : '로');
    return String(word) + (hasFinal(word) ? p[0] : p[1]);
  }
  const JOSA_FIX_RE = /([\uAC00-\uD7A3A-Za-z0-9])((?:\((?:[^()]|\([^()]*\))*\))+)(으로|이나|이며|이고|은|는|이|가|을|를|과|와|로|나|며|고)(?=[\s,.;:!?)」』"'”’]|$)/g;
  const JOSA_KEY = { '으로': '으로', '로': '으로', '이나': '이나', '나': '이나', '이며': '이며', '며': '이며', '이고': '이고', '고': '이고',
    '은': '은', '는': '은', '이': '이', '가': '이', '을': '을', '를': '을', '과': '과', '와': '과' };
  function fixJosa(text) {
    if (typeof text !== 'string' || text.indexOf(')') < 0) return text;
    return text.replace(JOSA_FIX_RE, (m, c, br, pa) => c + br + josa(c, JOSA_KEY[pa]).slice(c.length));
  }
  function fixDeep(v) {
    if (typeof v === 'string') return fixJosa(v);
    if (Array.isArray(v)) { for (let i = 0; i < v.length; i++) v[i] = fixDeep(v[i]); return v; }
    if (v && typeof v === 'object') { for (const k of Object.keys(v)) v[k] = fixDeep(v[k]); return v; }
    return v;
  }
  fixDeep(S);

  function shortName(name, opts = {}) {
    const full = String(name == null ? '' : name);
    let s = full, prev;
    const re = opts.brackets ? /\([^()\[\]]*\)|\[[^()\[\]]*\]/g : /\([^()]*\)/g;
    do { prev = s; s = s.replace(re, ''); } while (s !== prev);
    s = s.replace(/\s{2,}/g, ' ').trim();
    const bad = /[()]/.test(s) || (opts.brackets && /[\[\]]/.test(s)) || !s;
    const short = bad ? full : s;
    return { short, full, changed: short !== full };
  }
  function countWord(n) {
    return n === 2 ? cp('wordTwo') : n === 3 ? cp('wordThree') : fmt(n) + cp('sameCountSuffix');
  }
  function sameSummary(vals, eq = (a, b) => a === b) {
    const have = ORG_ORDER.filter(o => vals[o] != null && vals[o] !== '');
    const all = ORG_ORDER.filter(o => o in vals);
    if (have.length < 2) return have.length ? cp('sameOnlyOneTpl', { org: ORG_SHORT[have[0]] }) : cp('sameNone');
    const same = have.every(o => eq(vals[o], vals[have[0]]));
    if (!same) return cp('sameDiff');
    if (have.length === all.length) return cp('sameAllTpl', { n: countWord(all.length) });
    return cp('sameHaveTpl', { n: countWord(have.length) });
  }
  const orgShort = code => ORG_SHORT[code] || code;
  const vinfo = vid => S['종형'][vid] || null;
  const vname = vid => (vinfo(vid) ? vinfo(vid)['이름'] : vid);
  const vkind = vid => (vinfo(vid) ? vinfo(vid)['종형명'] : vid);
  const sinceText = since => {
    if (since == null) return cp('condNoHist');
    const row = (S['지도']['전체']['행'] || []).find(r => r['종류'] === '입원' && r.since === since);
    if (!row) return `${since}${cp('condSinceUnit')}`;
    return since === 5 ? cp('condSince5') : row['이름'].replace(/^입원\s*/, '');
  };
  const sexText = s => (s === 'F' ? cp('condFemale') : cp('condMale'));
  function stateWhy(org, state) {
    const n = orgShort(org);
    if (state === '나이 자료 없음') return cp('whyNoAgeTpl', { org: n });
    if (state === '질문 자료 없음') return cp('whyNoQstTpl', { org: n });
    return '';
  }

  // ---------- 상태 ----------
  const PEER_SCOPES = ['all', 'life', 'nonlife', 'custom'];
  const st = {
    tab: 'brief',
    age: REF['나이'] || 50,
    sex: REF['성별'] || 'M',
    since: REF['이력'] == null ? null : REF['이력'],
    surg: false,
    base: BASES[0]['종형ID'],
    renewal: null,
    peerScope: 'all',
    peerPick: PEER_ORGS.slice(),
    grp: {},
    sel: {},
    sub: {},
    skin: 'light',
    motion: 'on',
  };
  const listeners = { change: [], tab: [], select: [], sub: [], resize: [] };
  const tabs = {};
  let booted = false;
  let condOpen = false;
  let scopeOpen = false;
  let lastRenderedTab = 'brief';

  function activePeerOrgs(s = st) {
    const sc = s.peerScope || 'all';
    if (sc === 'life') return PEER_ORGS.filter(o => orgSector(o) === 'life');
    if (sc === 'nonlife') return PEER_ORGS.filter(o => orgSector(o) === 'nonlife');
    if (sc === 'custom') {
      const picked = new Set(Array.isArray(s.peerPick) ? s.peerPick : []);
      return PEER_ORGS.filter(o => picked.has(o));
    }
    return PEER_ORGS.slice();
  }
  function activeOrgs(s = st) { return ['EPOST'].concat(activePeerOrgs(s)); }
  function inScope(codes, s = st) {
    if (!Array.isArray(codes) || !codes.length) return 0;
    if ((s.peerScope || 'all') === 'all') return codes.length;
    const setP = new Set(activePeerOrgs(s));
    let n = 0;
    for (let i = 0; i < codes.length; i++) if (setP.has(codes[i])) n++;
    return n;
  }
  function filterScopeCodes(codes, s = st) {
    if (!Array.isArray(codes) || !codes.length) return [];
    if ((s.peerScope || 'all') === 'all') return codes.slice();
    const setP = new Set(activePeerOrgs(s));
    return codes.filter(c => setP.has(c));
  }

  // ---------- 공통 자료 집계(판정을 새로 만들지 않고 기관코드 교집합 크기만 센다) ----------
  function cellCounts(cell, s = st) {
    if (!cell) {
      return {
        open: 0, partial: 0, gateOnly: 0, openConfirmed: 0, closed: 0, unknown: 0,
        total: 0, openAny: 0, oursOpen: false, oursState: '', partialOnly: false, state: 'unknown',
      };
    }
    const open = inScope(cell['열린상대코드'], s);
    const partial = inScope(cell['일부열린상대코드'], s);
    const gateOnly = inScope(cell['관문만열린상대코드'], s);
    const openConfirmed = Math.max(0, open - gateOnly);
    const closed = inScope(cell['닫힌상대코드'], s);
    const unknown = inScope(cell['모르는상대코드'], s);
    const total = open + partial + closed + unknown;
    const openAny = open + partial;
    const oursState = (cell['회사'] && cell['회사'].EPOST) || '';
    const oursOpen = oursState === '열림';
    const partialOnly = open === 0 && partial > 0;
    let state = 'none';
    if (!oursOpen && openAny > 0) state = 'worse';
    else if (oursOpen && openAny === 0) state = 'only';
    else if (oursOpen && openAny > 0) state = 'both';
    else if ((!oursOpen && total > 0 && unknown === total) || cell['라벨'] === '자료 없음') state = 'unknown';
    return {
      open, partial, gateOnly, openConfirmed, closed, unknown,
      total, openAny, oursOpen, oursState, partialOnly, state,
    };
  }

  function gateFlowRows(map, cell, s = st) {
    const gm = S['관문마디'] || { '차례': [], '전제': [], '멈춘값': [] };
    const steps = gm['차례'] || [];
    const premiseSet = new Set(gm['전제'] || []);
    const types = (map && map['고지유형']) || [];
    const flowTypes = (cell && cell['관문흐름'] && cell['관문흐름']['유형']) || [];
    const flowByKey = {};
    flowTypes.forEach(f => { flowByKey[f['열쇠']] = f; });
    return types.map(meta => {
      const key = meta['열쇠'];
      const total = inScope(meta['상대코드'], s);
      const fl = flowByKey[key] || null;
      const pass = [];
      const stops = [];
      let stoppedSoFar = 0;
      for (let k = 0; k < steps.length; k++) {
        const rawStop = (fl && fl['멈춤'] && fl['멈춤'][String(k)]) || {};
        const scopedStop = {};
        let stoppedHere = 0;
        for (const [reason, codes] of Object.entries(rawStop)) {
          const fc = filterScopeCodes(codes, s);
          if (fc.length) {
            scopedStop[reason] = fc;
            stoppedHere += fc.length;
          }
        }
        stoppedSoFar += stoppedHere;
        stops.push(scopedStop);
        if (!cell || !fl) pass.push(0);
        else if ((s.peerScope || 'all') === 'all') pass.push(fl['통과수'][k] != null ? fl['통과수'][k] : Math.max(0, total - stoppedSoFar));
        else pass.push(Math.max(0, total - stoppedSoFar));
      }
      return {
        key,
        total,
        codes: filterScopeCodes(meta['상대코드'], s),
        pass,
        finalPass: pass.length ? pass[pass.length - 1] : 0,
        stops,
        steps,
        premiseSet,
      };
    });
  }

  function stageOrderOf(baseId) {
    const b = S['기준별'] && S['기준별'][baseId || st.base];
    const cols = b && b['치료여정'] && b['치료여정']['열'];
    if (Array.isArray(cols) && cols.length) return cols;
    for (const v of Object.values(S['기준별'] || {})) {
      const c2 = v && v['치료여정'] && v['치료여정']['열'];
      if (Array.isArray(c2) && c2.length) return c2;
    }
    const seen = [];
    for (const info of Object.values(S['표준담보'] || {})) {
      const tp = info && info['급부유형'];
      if (tp && !seen.includes(tp)) seen.push(tp);
    }
    return seen;
  }
  function coverStageStacks(baseId, s = st) {
    const B = window.App && App.cover && typeof App.cover.rawB === 'function' ? App.cover.rawB(baseId) : null;
    const stages = stageOrderOf(baseId).map(nm => ({
      name: nm,
      oursCnt: 0,
      totalCnt: 0,
      better: 0,
      neutral: 0,
      worse: 0,
      wait: 0,
      miss: 0,
      sum: 0,
    }));
    const byStage = Object.fromEntries(stages.map(stObj => [stObj.name, stObj]));
    if (!B || !Array.isArray(B.rows)) return stages;
    const isAll = (s.peerScope || 'all') === 'all';
    B.rows.forEach(r => {
      const sid = r[0];
      const info = S['표준담보'][sid] || {};
      const stg = byStage[info['급부유형']];
      if (!stg) return;
      stg.totalCnt++;
      const mine = r[1] && r[1][0];
      const oursHas = !!(mine && typeof mine === 'object' && Array.isArray(mine.i) && mine.i.length);
      if (oursHas) stg.oursCnt++;
      const perCodes = (B['판정기관코드'] && B['판정기관코드'][sid]) || {};
      const perCounts = (B['판정상대수'] && B['판정상대수'][sid]) || {};
      const cntOf = vdKey => (isAll ? (perCounts[vdKey] || 0) : inScope(perCodes[vdKey], s));
      const bCnt = cntOf('나음');
      const nCnt = cntOf('같음') + cntOf('엇갈림') + cntOf('단정 주의') + cntOf('지급 형태 다름') + cntOf('관계 담보로 덮음');
      const wCnt = cntOf('못함');
      const wtCnt = cntOf('검토 대기') + cntOf('판정 보류');
      const mCnt = cntOf('우체국에 없음');
      stg.better += bCnt;
      stg.neutral += nCnt;
      stg.worse += wCnt;
      stg.wait += wtCnt;
      stg.miss += mCnt;
      stg.sum += bCnt + nCnt + wCnt + wtCnt + mCnt;
    });
    return stages;
  }

  function scopedPairs(baseId, pickSet) {
    const base = S['기준별'] && S['기준별'][baseId];
    const p = base && base['보류요약'];
    if (!p) return null;
    if (!pickSet) {
      return {
        total: p['공통담보쌍'] || 0,
        wait: p['뺀쌍'] || 0,
        cmp: p['견준쌍'] || 0,
        why: Object.assign({}, p['사유별'] || {}),
      };
    }
    const byOrg = p['기관별'] || {};
    let total = 0, wait = 0, cmp = 0;
    const why = {};
    for (const [org, per] of Object.entries(byOrg)) {
      if (!pickSet.has(org) || !per) continue;
      total += per['공통담보쌍'] || 0;
      wait += per['뺀쌍'] || 0;
      cmp += per['견준쌍'] || 0;
      for (const [rk, rv] of Object.entries(per['사유별'] || {})) {
        if (rv) why[rk] = (why[rk] || 0) + rv;
      }
    }
    return { total, wait, cmp, why };
  }

  function mapOf(renewal) { return S['지도'][MAP_KEY[renewal]] || S['지도']['전체']; }
  function cellOf(s = st) {
    const m = mapOf(s.renewal);
    const kind = (s.since != null && s.surg) ? '수술만' : '입원';
    const since = s.since == null ? 5 : s.since;
    const ri = m['행'].findIndex(r => r['종류'] === kind && r.since === since);
    const ci = m['열'].findIndex(c => s.age >= c.lo && s.age <= c.hi);
    const lo = m['열'][0].lo, hi = m['열'][m['열'].length - 1].hi;
    const out = { map: m, ri, ci, row: m['행'][ri] || null, col: m['열'][ci] || null, cell: null, reason: '', sexNote: '' };
    if (ci < 0) out.reason = cp('whySegAgeTpl', { lo, hi });
    else if (ri < 0) out.reason = cp('whySegRow');
    // 이력 없음은 지도의 "5년+" 칸(ri)에 표시하되, 값은 이력없음(이력 없는 고객으로 계산한 값)을 읽는다(API.md)
    else out.cell = (s.since == null && m['이력없음'] && m['이력없음'][ci]) || m['칸'][ri][ci];
    if (s.sex !== m['성별']) out.sexNote = cp('whySegSexTpl', { sex: sexText(s.sex), mapSex: sexText(m['성별']) });
    return out;
  }
  function segPatch(m, ri, ci, s = st) {
    const row = m['행'][ri], col = m['열'][ci], cell = (m['칸'][ri] || [])[ci] || null;
    if (!row || !col) return null;
    const age = s.age >= col.lo && s.age <= col.hi ? s.age : col.lo;
    let since = row.since;
    if (row.since === 5 && row['종류'] === '입원' && s.since == null) since = null;
    const patch = { age, since, surg: row['종류'] === '수술만' };
    if (cell && cell['대표'] && BASES.some(b => b['종형ID'] === cell['대표'])) patch.base = cell['대표'];
    return patch;
  }
  const segPatchText = p => `${p.age}${cp('condAgeUnit')}, ${p.since == null ? cp('condNoHist') : `${p.surg ? cp('condSurgOnly') : cp('condHospOrSurg')} ${sinceText(p.since)}`}${p.base ? `, ${cp('condBase')} ${vkind(p.base)}` : ''}`;
  const samePatch = (p, s = st) => Object.keys(p).every(k => JSON.stringify(p[k]) === JSON.stringify(s[k]));

  function limitOf(s = st) {
    const t = (S['한도표'] || []).find(x => x['종형ID'] === s.base);
    if (!t) return null;
    const seg = (t['구간'][s.sex] || []);
    const hit = seg.find(g => s.age >= g.lo && s.age <= g.hi);
    const lo = seg.length ? seg[0].lo : null, hi = seg.length ? seg[seg.length - 1].hi : null;
    return { table: t, hit: hit || null, lo, hi };
  }
  const isRefCond = () => st.age === REF['나이'] && st.sex === REF['성별'] && st.since === REF['이력'] && !st.surg;

  function ctx(changed) {
    const base = S['기준별'][st.base];
    const pOrgs = activePeerOrgs();
    const pSet = new Set(pOrgs);
    const rawPeerIds = base ? base['맞붙는종형'] : [];
    const filteredPeerIds = st.peerScope === 'all' ? rawPeerIds : rawPeerIds.filter(id => pSet.has((vinfo(id) || {})['기관코드']));
    return {
      S, D: DD,
      st: { ...st, peerPick: st.peerPick.slice(), grp: { ...st.grp }, sel: { ...st.sel }, sub: { ...st.sub } },
      changed: changed || new Set(),
      baseId: st.base, base, baseInfo: vinfo(st.base),
      peerIds: filteredPeerIds, peers: filteredPeerIds.map(vinfo),
      allPeerIds: rawPeerIds,
      peerScope: st.peerScope, activePeerOrgs: pOrgs, activeOrgs: ['EPOST'].concat(pOrgs),
      inScope: codes => inScope(codes, st),
      filterScopeCodes: codes => filterScopeCodes(codes, st),
      cellCounts: cell => cellCounts(cell, st),
      gateFlowRows: (m, cell) => gateFlowRows(m, cell, st),
      coverStageStacks: bid => coverStageStacks(bid || st.base, st),
      seg: cellOf(), limit: limitOf(), ref: REF, isRef: isRefCond(),
      ui: UI, txt: TXT, t: cp,
    };
  }

  function set(patch, opts = {}) {
    const changed = new Set();
    for (const [k, v] of Object.entries(patch)) {
      if (!(k in st)) continue;
      if ((k === 'sel' || k === 'sub' || k === 'grp') && (!v || typeof v !== 'object')) continue;
      if (JSON.stringify(st[k]) !== JSON.stringify(v)) { st[k] = v; changed.add(k); }
    }
    if (!changed.size) return;
    if (changed.has('since') && st.since == null && st.surg) { st.surg = false; changed.add('surg'); }
    if (changed.has('skin')) applySkin();
    if (changed.has('motion')) applyMotion();
    const shouldAutoCloseCond = ['age', 'sex', 'since', 'surg', 'base', 'renewal'].some(k => changed.has(k)) && !opts.keepCond && condOpen;
    if (opts.push !== false && booted) pushHistory(changed);
    if (changed.has('tab') && changed.size === 1) { showTab(st.tab, opts); return; }
    if (changed.has('tab')) showTab(st.tab, { scroll: false });
    notify(changed, opts);
    if (shouldAutoCloseCond) setCondOpen(false);
  }
  function on(ev, fn) { (listeners[ev] || (listeners[ev] = [])).push(fn); }
  function emit(ev, ...args) { for (const fn of (listeners[ev] || [])) { try { fn(...args); } catch (e) { console.error(e); } } }
  const mode = () => (innerWidth >= 1600 ? 'wide' : innerWidth >= 1000 ? 'push' : 'sheet');
  const motionOn = () => st.motion !== 'off';
  const motionRich = () => st.motion === 'on';
  const motionScale = () => (st.motion === 'on' ? 1 : st.motion === 'calm' ? 0.55 : 0);

  function countUp(root) {
    if (!motionRich()) return;
    const els = $$('[data-count-to]', root || document);
    if (!els.length) return;
    const dur = 480;
    const t0 = performance.now();
    const targets = els.map(el => ({
      el,
      to: +el.dataset.countTo || 0,
      suffix: el.dataset.countSuffix || '',
    }));
    targets.forEach(x => { x.el.textContent = fmt(0) + x.suffix; });
    function tick(now) {
      const p = Math.min(1, (now - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      for (const x of targets) {
        if (!x.el.isConnected) continue;
        x.el.textContent = fmt(Math.round(x.to * eased)) + x.suffix;
      }
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // ---------- 주소(#)와 뒤로 가기 ----------
  function encodeHash() {
    const p = new URLSearchParams();
    if (st.tab !== 'brief') p.set('t', st.tab);
    if (st.age !== REF['나이']) p.set('a', st.age);
    if (st.sex !== REF['성별']) p.set('s', st.sex);
    if (st.since !== REF['이력']) p.set('h', st.since == null ? 'none' : st.since);
    if (st.surg) p.set('u', '1');
    if (st.base !== BASES[0]['종형ID']) p.set('b', st.base);
    if (st.renewal) p.set('r', st.renewal);
    if (st.peerScope && st.peerScope !== 'all') {
      p.set('ps', st.peerScope);
      if (st.peerScope === 'custom') p.set('pp', (st.peerPick || []).join(','));
    }
    const g = st.grp[st.tab];
    if (g != null && g !== '') p.set('g', g);
    const pick = st.sel[st.tab];
    if (pick != null) p.set('k', pick);
    const q = p.toString();
    return q ? '#' + q : location.pathname + location.search;
  }
  function decodeHash(hash) {
    const p = new URLSearchParams((hash || '').replace(/^#/, ''));
    const out = {};
    const t = p.get('t');
    out.tab = TAB_IDS.includes(t) ? t : 'brief';
    const a = p.get('a'); out.age = a != null && !isNaN(+a) ? Math.min(100, Math.max(1, Math.round(+a))) : REF['나이'];
    const s = p.get('s'); out.sex = (s === 'F' || s === 'M') ? s : REF['성별'];
    const h = p.get('h'); out.since = h === 'none' ? null : (h != null && [0.25, 1, 2, 3, 4, 5].includes(+h) ? +h : REF['이력']);
    out.surg = p.get('u') === '1' && out.since != null;
    const b = p.get('b'); out.base = BASES.some(x => x['종형ID'] === b) ? b : BASES[0]['종형ID'];
    const r = p.get('r'); out.renewal = (r === '갱신' || r === '비갱신') ? r : null;
    const ps = p.get('ps'); out.peerScope = PEER_SCOPES.includes(ps) ? ps : 'all';
    const pp = p.get('pp');
    out.peerPick = out.peerScope === 'custom' && pp != null
      ? pp.split(',').filter(c => PEER_ORGS.includes(c))
      : PEER_ORGS.slice();
    return { patch: out, grp: p.get('g'), pick: p.get('k') };
  }
  let inPop = false;
  function pushHistory(changed) {
    if (inPop) return;
    const url = encodeHash();
    const onlyAge = changed.size === 1 && changed.has('age');
    try {
      if (onlyAge) history.replaceState({ c4: 1 }, '', url);
      else history.pushState({ c4: 1 }, '', url);
    } catch (e) { /* */ }
  }
  addEventListener('popstate', () => {
    inPop = true;
    closeModal(false);
    const { patch, grp, pick } = decodeHash(location.hash);
    st.grp = {};
    if (grp != null) st.grp[patch.tab] = grp;
    st.sel = {};
    st.sub = {};
    if (pick != null) st.sel[patch.tab] = pick;
    set(patch, { push: false, keepCond: true });
    applySelectionState(false);
    inPop = false;
  });

  // ---------- 아이콘과 공통 UI 부품 ----------
  const IC = {
    chevR: '<svg width="8" height="14" viewBox="0 0 8 14" aria-hidden="true"><path d="M1 1l6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
    chevL: '<svg width="8" height="14" viewBox="0 0 8 14" aria-hidden="true"><path d="M7 1L1 7l6 6" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
    chevD: '<svg width="12" height="8" viewBox="0 0 12 8" aria-hidden="true"><path d="M1 1l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
    better: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 1.5L9 8.5H1Z" fill="currentColor"/></svg>',
    only: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 1L9 5 5 9 1 5Z" fill="currentColor"/></svg>',
    worse: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1 1.5h8L5 8.5Z" fill="currentColor"/></svg>',
    same: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1.5 3.5h7M1.5 6.5h7" stroke="currentColor" stroke-width="1.6"/></svg>',
    diff: '<svg viewBox="0 0 12 10" aria-hidden="true"><path d="M1 3h9M7.5 1L10 3 7.5 5M11 7H2M4.5 5L2 7l2.5 2" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>',
    none: '<svg viewBox="0 0 10 10" aria-hidden="true"><rect x="1.5" y="1.5" width="7" height="7" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="2 1.5"/></svg>',
    unknown: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M3.2 3.3a1.85 1.65 0 1 1 2.7 1.45c-.6.35-.9.68-.9 1.35" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="square"/><rect x="4.3" y="7.4" width="1.4" height="1.4" fill="currentColor"/></svg>',
    lock: '<svg width="12" height="13" viewBox="0 0 12 13" aria-hidden="true"><rect x="1.5" y="5.5" width="9" height="6.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M3.5 5.5V4a2.5 2.5 0 0 1 5 0v1.5" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>',
    copy: '<svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true"><rect x="4" y="4" width="7.5" height="7.5" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M9 4V1.5H1.5V9H4" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>',
    print: '<svg width="14" height="13" viewBox="0 0 14 13" aria-hidden="true"><path d="M3.5 4V1.5h7V4M3.5 9.5H1.5V5h11v4.5h-2M3.5 7.5h7v4h-7Z" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>',
    grid: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><path d="M1 1h2v2H1ZM4.5 1h2v2h-2ZM8 1h2v2H8ZM1 4.5h2v2H1ZM4.5 4.5h2v2h-2ZM8 4.5h2v2H8ZM1 8h2v2H1ZM4.5 8h2v2h-2ZM8 8h2v2H8Z" fill="currentColor"/></svg>',
    pin: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><rect x="1.2" y="1.2" width="8.6" height="8.6" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="3.8" y="3.8" width="3.4" height="3.4" fill="currentColor"/></svg>',
    open: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><rect x="1.5" y="1.5" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
    check: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><rect x="1.5" y="1.5" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.3" stroke-dasharray="2 1.5"/></svg>',
    hatch: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><rect x="1" y="1" width="9" height="9" fill="none" stroke="currentColor" stroke-width="1.1" stroke-dasharray="2 1.5"/><path d="M2 9L9 2" stroke="currentColor" stroke-width="1.1"/></svg>',
    arrow: '<svg width="14" height="10" viewBox="0 0 14 10" aria-hidden="true"><path d="M1 5h11M8.5 1.5L12 5 8.5 8.5" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>',
    table: '<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><rect x="1" y="1.5" width="10" height="9" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M1 4.5h10M4.5 4.5v6" stroke="currentColor" stroke-width="1.1"/></svg>',
    doc: '<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 1.2h5.6L10 3.6v7.2H2Z" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M4 5.5h4M4 7.8h4" stroke="currentColor" stroke-width="1.1"/></svg>',
    moon: '<svg class="tgl-ic" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M8.8 7.8A4.2 4.2 0 0 1 4.2 3.2a4.2 4.2 0 1 0 4.6 4.6Z" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>',
    wave: '<svg class="tgl-ic" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M1 6h2.2l1.4-3.2 2.4 6.4 1.6-3.2H11" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>',
    legend: '<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><rect x="1" y="1.5" width="2.5" height="2.5" fill="currentColor"/><path d="M5 2.8h6M5 6h6M5 9.2h6" stroke="currentColor" stroke-width="1.4"/><rect x="1" y="4.8" width="2.5" height="2.5" fill="none" stroke="currentColor" stroke-width="1.1"/><path d="M2.2 8l1.3 2.3H1Z" fill="currentColor"/></svg>',
  };

  const VERDICT = {
    better: { cls: 'vd-better', ic: IC.better, t: () => cp('vdBetter') },
    only: { cls: 'vd-only', ic: IC.only, t: () => cp('vdOnly') },
    worse: { cls: 'vd-worse', ic: IC.worse, t: () => cp('vdWorse') },
    same: { cls: 'vd-same', ic: IC.same, t: () => cp('vdSame') },
    diff: { cls: 'vd-diff', ic: IC.diff, t: () => cp('vdDiff') },
    none: { cls: 'vd-none', ic: '', t: () => cp('vdNone') },
    unknown: { cls: 'vd-unknown', ic: IC.unknown, t: () => cp('vdUnknown') },
  };
  function verdict(kind, text, titleText) {
    const v = VERDICT[kind] || VERDICT.unknown;
    const ttl = titleText ? ` title="${esc(titleText)}"` : '';
    return `<span class="vd ${v.cls}"${ttl}>${v.ic}<span>${esc(text != null ? text : v.t())}</span></span>`;
  }
  const FLAG_TEXT = COPY.flagDefault;
  function flag(text) {
    const t = text || cp('flagDefault');
    return `<span class="flag" role="img" aria-label="${esc(t)}" data-tip="${esc(t)}" title="${esc(t)}"><i></i></span>`;
  }
  function flagText(text) {
    const t = text || cp('flagDefault');
    return `<span class="flag-t"><span class="tri" aria-hidden="true"><i></i></span><span>${esc(t)}</span></span>`;
  }
  function scope(kind) {
    if (kind === 'all' || kind === cp('scopeAll')) return `<span class="scb scb-all" title="${esc(cp('scopeAllHint'))}">${IC.grid}<span>${esc(cp('scopeAll'))}</span></span>`;
    if (kind === 'now' || kind === cp('scopeNow')) return `<span class="scb scb-now" title="${esc(cp('scopeNowHint'))}">${IC.pin}<span>${esc(cp('scopeNow'))}</span></span>`;
    return `<span class="scb scb-base" title="${esc(cp('scopeBaseHint'))}">${IC.pin}<span>${esc(cp('scopeBase'))}</span></span>`;
  }
  function fullScopeTag() {
    return st.peerScope === 'all' ? '' : `<span class="tag" title="${esc(cp('fullScopeHint'))}">${esc(cp('fullScopeBadge'))}</span>`;
  }
  function tag(text, titleText, cls) {
    return `<span class="tag${cls ? ' ' + cls : ''}"${titleText ? ` title="${esc(titleText)}"` : ''}>${esc(text)}</span>`;
  }
  function name(full, opts) {
    const r = shortName(full, opts);
    return r.changed ? `<span title="${esc(r.full)}">${esc(r.short)}</span>` : esc(r.short);
  }
  function title(id, kicker, text) {
    return `<div class="ttl"><nav class="lpath" aria-label="${esc(cp('pathAria'))}"></nav><h2 class="ttl-t">${esc(text)}</h2></div>`;
  }
  function big(n, denom, unit) {
    const d = denom != null ? `<span class="d">/${esc(fmt(denom))}</span>` : '';
    const u = unit ? `<span class="u">${esc(unit)}</span>` : '';
    return `<span class="big num"><span class="n">${esc(fmt(n))}</span>${d}${u}</span>`;
  }

  function ring(opts) {
    const size = opts.size || 72, r = 28, sw = opts.stroke || 3.4;
    const max = Math.max(0.0001, +opts.max || 1);
    const segs = opts.segs || [{ v: +opts.v || 0, cls: opts.gold ? 'gold' : '' }];
    const sum = Math.min(max, segs.reduce((a, s) => a + (+s.v || 0), 0));
    const f = sum / max;
    const C = +(2 * Math.PI * r).toFixed(2);
    let off = 0;
    const arcs = segs.filter(s => s.v > 0).map(s => {
      const len = +(C * Math.min(1, s.v / max)).toFixed(2);
      const dash = `${len} ${C}`;
      const el = `<circle class="arc${s.cls ? ' ' + s.cls : ''}" r="${r}" fill="none" stroke-width="${sw}" stroke-dasharray="${dash}" data-dash="${dash}" data-c="${C}" stroke-dashoffset="${-off}" transform="rotate(-90)"/>`;
      off += len;
      return el;
    }).join('');
    let ticks = '';
    if (f < 0.999) {
      const N = 36, r1 = r - 2.4, r2 = r + 2.4;
      const lines = [];
      for (let i = 0; i < N; i++) {
        if (i / N < f - 0.004) continue;
        const a = (i / N) * 2 * Math.PI - Math.PI / 2;
        lines.push(`<line x1="${(r1 * Math.cos(a)).toFixed(1)}" y1="${(r1 * Math.sin(a)).toFixed(1)}" x2="${(r2 * Math.cos(a)).toFixed(1)}" y2="${(r2 * Math.sin(a)).toFixed(1)}" stroke-width="1"/>`);
      }
      ticks = `<g class="tks">${lines.join('')}</g>`;
    }
    const diag = (opts.lead || opts.sel)
      ? '<g class="diag" stroke-width="1.2"><line x1="-30" y1="-30" x2="-23" y2="-23"/><line x1="30" y1="-30" x2="23" y2="-30"/><line x1="-30" y1="30" x2="-23" y2="23"/><line x1="30" y1="30" x2="23" y2="23"/></g>'
      : '';
    const disc = opts.sel ? `<circle class="disc" r="${r - 3}"/>` : '';
    const txtEl = opts.pct != null ? `<text class="pct" y="8" text-anchor="middle">${esc(opts.pct)}</text>` : '';
    const aria = opts.label ? ` role="img" aria-label="${esc(opts.label)}"` : ' aria-hidden="true"';
    return `<svg class="ring${opts.sel ? ' sel' : ''}" width="${size}" height="${size}" viewBox="-36 -36 72 72"${aria}>
      ${diag}${disc}<circle class="trk" r="${r}" fill="none" stroke-width="1"/>${ticks}${arcs}${txtEl}</svg>`;
  }
  function drawRings(root) {
    if (!motionOn()) return;
    for (const c of $$('.ring .arc', root || document)) {
      const C = c.dataset.c, d = c.dataset.dash;
      if (!C || !d) continue;
      c.style.transition = 'none';
      c.setAttribute('stroke-dasharray', `0 ${C}`);
      void c.getBoundingClientRect();
      c.style.transition = '';
      c.setAttribute('stroke-dasharray', d);
    }
  }
  function hbar(v, max, cls) {
    const p = max > 0 ? Math.max(0, Math.min(1, v / max)) : 0;
    return `<span class="hbar" aria-hidden="true"><i class="${cls || ''}" style="width:100%;transform:scaleX(${p.toFixed(4)})"></i></span>`;
  }
  function btn(text, o = {}) {
    const cls = ['btn', o.main ? 'btn-main' : '', o.sm ? 'sm' : '', o.ghost ? 'ghost' : '', o.cls || ''].filter(Boolean).join(' ');
    const ic = o.icon ? (IC[o.icon] || o.icon) : '';
    const ch = o.chev ? IC.chevR : '';
    const at = o.attrs || '';
    const ttl = ic && !/aria-label=/.test(at) ? ` aria-label="${esc(text)}" title="${esc(text)}"` : '';
    return `<button type="button" class="${cls}"${ttl} ${at}>${ic}<span>${esc(text)}</span>${ch}</button>`;
  }

  const TERMS = {
    'scope-band': { titleKey: 'termScopeTitle', bodyKey: 'termScopeBody' },
    'ev-panel': { titleKey: 'termEvTitle', bodyKey: 'termEvBody' },
    'base-sel': { titleKey: 'termBaseTitle', bodyKey: 'termBaseBody' },
    'journey-grid': { titleKey: 'termJourneyTitle', bodyKey: 'termJourneyBody' },
    'caution-pending': { titleKey: 'termCautionTitle', bodyKey: 'termCautionBody' },
  };
  function help(termKey, label) {
    const item = TERMS[termKey];
    if (!item) return '';
    const nm = label || cp(item.titleKey);
    return `<button type="button" class="qhelp" data-help="${esc(termKey)}" aria-controls="help-pop" aria-label="${esc(nm + cp('helpSuffixAria'))}" aria-expanded="false">?</button>`;
  }

  const LEGENDS = {};
  function registerLegend(key, titleKey, htmlFn) {
    LEGENDS[key] = { titleKey, htmlFn };
  }
  function legendBtn(key, labelText) {
    const lb = labelText || cp('legendBtn');
    return `<button type="button" class="btn sm ghost leg-btn" data-legend="${esc(key || 'verdict')}" aria-controls="help-pop" aria-expanded="false" aria-label="${esc(lb)}" title="${esc(lb)}">${IC.legend}<span>${esc(lb)}</span></button>`;
  }

  const NOTE_HEAD = {
    '지도전제': 'noteHeadMap',
    '간편청약제한': 'noteHeadSimp',
    '수술만행': 'noteHeadSurg',
    '일반심사': 'noteHeadGen',
  };
  function notes(tabName) {
    const list = (S['주석'] || []).filter(n => !tabName || (n['탭'] || []).includes(tabName));
    if (!list.length) return '';
    return `<aside class="snotes" aria-label="${esc((tabName || '') + cp('notesAriaSuffix'))}">
      <h3 class="snotes-h">${esc(cp('notesTitle'))}${st.peerScope !== 'all' ? ' ' + fullScopeTag() : ''}</h3>
      <ul class="snotes-l">${list.map(n => {
        const hk = NOTE_HEAD[n['열쇠']];
        const hd = hk ? cp(hk) : n['열쇠'];
        return `<li><b>${esc(hd)}</b><span>${esc(n['글'])}</span>${n['출처'] ? `<span class="snotes-src">${esc(cp('notesSrcPrefix') + n['출처'])}</span>` : ''}</li>`;
      }).join('')}</ul></aside>`;
  }

  const RCHEV = `<span class="rchev" aria-hidden="true">${IC.chevR}</span>`;
  function table(o) {
    const numSet = new Set(o.num || []);
    const cap = o.caption ? `<caption>${esc(o.caption)}</caption>` : '';
    const th = o.head.map((h, i) => `<th scope="col"${numSet.has(i) ? ' class="v"' : ''}>${h}</th>`).join('');
    const last = o.head.length - 1;
    const tr = o.rows.map((cells, r) => {
      const pk = o.pick ? o.pick(r) : null;
      const tds = cells.map((c, i) => {
        const obj = c && typeof c === 'object' && !Array.isArray(c);
        const html = obj ? c.h : c;
        const cpAttr = obj && c.cp != null ? ` data-cp="${esc(c.cp)}"` : '';
        const cls = [numSet.has(i) ? 'v' : '', obj && c.cls ? c.cls : ''].filter(Boolean).join(' ');
        const tail = pk != null && i === last ? RCHEV : '';
        return `<td${cls ? ` class="${cls}"` : ''}${cpAttr}>${html}${tail}</td>`;
      }).join('');
      return pk != null
        ? `<tr class="pick" data-pick="${esc(pk)}" tabindex="0">${tds}</tr>`
        : `<tr${cells._cls ? ` class="${cells._cls}"` : ''}>${tds}</tr>`;
    }).join('');
    return `<table class="tbl"${o.id ? ` id="${esc(o.id)}"` : ''}>${cap}<thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`;
  }
  function band(o) {
    const scs = (Array.isArray(o.sc) ? o.sc : o.sc ? [o.sc] : []).map(scope).join(' ');
    const stats = (o.stats || []).map(s => `<div class="sb-st"${s.title ? ` title="${esc(s.title)}"` : ''}>
      ${big(s.n, s.d, s.u)}<span class="sb-l">${esc(s.l)}</span>${s.bar ? hbar(s.bar[0], s.bar[1], s.bar[2]) : ''}</div>`).join('');
    const noteHTML = o.noteHTML ? o.noteHTML : (o.note ? esc(o.note) : '');
    const foot = (o.eq || noteHTML) ? `<div class="sb-f">${o.eq || ''}${noteHTML ? `<p class="note">${noteHTML}</p>` : ''}</div>` : '';
    const hlp = o.help ? help(o.help, o.title) : '';
    return `<div class="sband"><div class="sb-t pillar"><i class="sb-tk" aria-hidden="true"></i>
      <span class="k">${scs}${o.kicker ? `<span>${esc(o.kicker)}</span>` : ''}</span><h2><span>${esc(o.title)}</span>${hlp}</h2></div>
      <div class="sb-s">${stats}</div>${foot}</div>`;
  }
  function eq(o) {
    const head = o.total ? `<span>${esc(o.total.t)}</span> <span class="n">${esc(fmt(o.total.n))}</span> <span class="op">=</span> ` : '';
    const body = o.parts.map((p, i) => `${i ? '<span class="op">+</span> ' : ''}<span>${esc(p.t)}</span> <span class="n">${esc(fmt(p.n))}</span>`).join(' ');
    const tail = o.tail ? ` <span class="nb">${esc(o.tail)}</span>` : '';
    const na = o.nonAdd ? `<div class="nadd">${esc(o.nonAdd)}</div>` : '';
    return `<div class="eq">${head}${body}${tail}</div>${na}`;
  }
  function fadeBand(html, o = {}) { return `<div class="fade-band${o.slate ? ' slate' : ''}">${html}</div>`; }
  function cells(kinds) { return `<div class="cqs" aria-hidden="true">${kinds.map(k => `<i class="cq ${k}"></i>`).join('')}</div>`; }
  const MAP_CLS = { '우리 간편만 열림': 'm-only', '함께 열림': 'm-both', '우리 간편 닫힘': 'm-ours', '간편 모두 닫힘': 'm-all', '자료 없음': 'm-none' };
  const swatch = label => `<i class="cq ${MAP_CLS[label] || 'm-none'}" aria-hidden="true"></i>`;

  function chevSel(o) {
    const el = document.createElement('div');
    el.className = 'chev-sel' + (o.num ? ' num' : '');
    if (o.w) el.style.setProperty('--w', o.w);
    el.innerHTML = `<button type="button" class="p" aria-label="${esc(o.label + cp('chevPrevSuffix'))}">${IC.chevL}</button><span class="v" aria-live="polite"></span><button type="button" class="n" aria-label="${esc(o.label + cp('chevNextSuffix'))}">${IC.chevR}</button>`;
    const opts = o.options;
    let idx = Math.max(0, opts.findIndex(x => x.v === o.value));
    const vEl = $('.v', el), pB = $('.p', el), nB = $('.n', el);
    function sync() {
      const cur = opts[idx];
      vEl.textContent = cur.t;
      vEl.title = cur.title || '';
      if (!o.wrap) { pB.disabled = idx <= 0; nB.disabled = idx >= opts.length - 1; }
    }
    function step(d) {
      const next = o.wrap ? (idx + d + opts.length) % opts.length : Math.max(0, Math.min(opts.length - 1, idx + d));
      if (next === idx) return;
      idx = next; sync(); o.onChange(opts[idx].v);
    }
    pB.addEventListener('click', () => step(-1));
    nB.addEventListener('click', () => step(1));
    el.tabIndex = 0;
    el.setAttribute('role', 'spinbutton');
    el.setAttribute('aria-label', o.label);
    el.addEventListener('keydown', e => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') { e.preventDefault(); step(-1); }
      if (e.key === 'ArrowRight' || e.key === 'ArrowUp') { e.preventDefault(); step(1); }
    });
    el.set = val => { const i = opts.findIndex(x => x.v === val); if (i >= 0) { idx = i; sync(); } };
    sync();
    return el;
  }
  function stepper(o) {
    const el = document.createElement('div');
    el.className = 'chev-sel num';
    el.style.setProperty('--w', o.w || '60px');
    el.innerHTML = `<button type="button" class="p" aria-label="${esc(o.label + cp('stepDecSuffix'))}">${IC.chevL}</button><input type="text" inputmode="numeric" aria-label="${esc(o.label)}"><button type="button" class="n" aria-label="${esc(o.label + cp('stepIncSuffix'))}">${IC.chevR}</button>`;
    const inp = $('input', el), pB = $('.p', el), nB = $('.n', el);
    let cur = o.value;
    const clamp = v => Math.max(o.min, Math.min(o.max, Math.round(v)));
    function commit(v, keepCond) {
      if (isNaN(v)) { el.set(cur); return; }
      cur = clamp(v); el.set(cur); o.onChange(cur, keepCond);
    }
    el.set = v => { cur = v; inp.value = v + (o.unit || ''); pB.disabled = cur <= o.min; nB.disabled = cur >= o.max; };
    pB.addEventListener('click', () => commit(cur - 1, true));
    nB.addEventListener('click', () => commit(cur + 1, true));
    inp.addEventListener('focus', () => { inp.value = String(cur); inp.select(); });
    inp.addEventListener('blur', () => commit(parseInt(inp.value, 10), false));
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') { inp.blur(); e.preventDefault(); }
      if (e.key === 'ArrowUp') { commit(cur + 1, true); e.preventDefault(); }
      if (e.key === 'ArrowDown') { commit(cur - 1, true); e.preventDefault(); }
    });
    el.set(o.value);
    return el;
  }

  const pageText = (doc, page) => (page != null && page !== '' ? `${doc || cp('docFallback')} ${page}${cp('pageSuffix')}` : `${doc || cp('docFallback')}${cp('pageMissingSuffix')}`);
  const PAGE_WHY = cp('pageWhy');

  const UI = { esc, fmt, firstSentence, t: cp, IC, verdict, flag, flagText, FLAG_TEXT, scope, fullScopeTag, tag, name, title, big, ring, drawRings, countUp, hbar, btn, table, RCHEV, band, eq, fadeBand, cells, MAP_CLS, swatch, chevSel, stepper, help, legendBtn, registerLegend, notes };
  const TXT = { josa, fixJosa, hasFinal, shortName, sameSummary, orgShort, orgSector, vname, vkind, vinfo, sinceText, sexText, stateWhy, pageText, PAGE_WHY, ORG_ORDER, PEER_ORGS, ORG_SHORT, firstSentence };

  // ---------- 진행 추적기 머리와 접히는 조건 편집 판 ----------
  const SINCE_OPTS = [{ v: null, t: cp('condNoHist') }].concat(
    S['지도']['전체']['행'].filter(r => r['종류'] === '입원').map(r => ({ v: r.since, t: r.since === 5 ? cp('condSince5') : r['이름'].replace(/^입원\s*/, '') })));
  const C = {};

  function peerScopeLabel() {
    if (st.peerScope === 'life') return cp('peerLifeGroup');
    if (st.peerScope === 'nonlife') return cp('peerNonLifeGroup');
    if (st.peerScope === 'custom') return cp('peerCustomShortTpl', { n: activePeerOrgs().length });
    return cp('peerAll');
  }
  function peerNamesShort(list) {
    if (!list.length) return cp('condPeerNone');
    if (list.length <= 2) return list.join(', ');
    return cp('peerRestTpl', { first: list[0], rest: list.length - 1 });
  }
  function peerNamesEtc(list, cap = 3) {
    if (!list.length) return cp('mkRevNone');
    if (list.length <= cap) return list.join(', ');
    return cp('peerEtcTpl', { names: list.slice(0, cap).join(', '), total: fmt(list.length) });
  }
  TXT.peerNamesShort = peerNamesShort;
  TXT.peerNamesEtc = peerNamesEtc;

  function condSummary() {
    const hist = st.since == null ? cp('condNoHist') : `${st.surg ? cp('condSurgOnly') : cp('condHospOrSurg')} ${sinceText(st.since)}`;
    const base = S['기준별'][st.base];
    const pSet = new Set(activePeerOrgs());
    const rawOrgs = base
      ? [...new Set(base['맞붙는종형'].map(v => (vinfo(v) || {})['기관코드']).filter(Boolean))]
      : [];
    const shownOrgs = st.peerScope === 'all' ? rawOrgs : rawOrgs.filter(o => pSet.has(o));
    const peers = peerNamesShort(shownOrgs.map(orgShort));
    return `${st.age}${cp('condAgeUnit')} ${sexText(st.sex)}, ${hist} / ${cp('condBasePrefix')} ${vkind(st.base)} / ${cp('condPeerPrefix')} ${peers}`;
  }
  function condSegOnly() {
    const hist = st.since == null ? cp('condNoHist') : `${st.surg ? cp('condSurgOnly') : cp('condHospOrSurg')} ${sinceText(st.since)}`;
    return `${st.age}${cp('condAgeUnit')} ${sexText(st.sex)}, ${hist}`;
  }

  function parseDurMs(raw, fallback) {
    if (!raw) return fallback;
    const s = String(raw).trim();
    if (s.endsWith('ms')) { const v = parseFloat(s); return isNaN(v) ? fallback : v; }
    if (s.endsWith('s')) { const v = parseFloat(s); return isNaN(v) ? fallback : v * 1000; }
    const v = parseFloat(s);
    return isNaN(v) ? fallback : v;
  }
  function panelTiming(isOpen, distPx) {
    if (!motionOn()) return { dur: 0, easing: 'linear' };
    const cs = getComputedStyle(document.documentElement);
    const prop = isOpen ? '--dur-panel-open' : '--dur-panel-close';
    let dur = parseDurMs(cs.getPropertyValue(prop), isOpen ? 400 : 320);
    if (st.motion === 'on' && distPx && Math.abs(distPx) > 184) {
      dur = Math.min(600, Math.max(dur, Math.ceil(1.76 * Math.abs(distPx))));
    }
    const easing = (cs.getPropertyValue('--ease-panel') || '').trim() || 'cubic-bezier(0.2, 0, 0.8, 1)';
    return { dur, easing };
  }

  function belowElementsOf(bandEl) {
    const out = [];
    if (bandEl && bandEl.id === 'cond') {
      const sc = $('#scope');
      if (sc && !sc.hidden) out.push(sc);
    }
    const rt = $('#rtabs-wrap');
    if (rt && !rt.hidden) out.push(rt);
    const hp = $('#home-panel');
    if (hp && !hp.hidden) out.push(hp);
    const bd = $('#board');
    if (bd && !bd.hidden) {
      const zl = $('#z-left'), zc = $('#z-center'), zr = $('#z-right');
      if (zl && !zl.hidden) out.push(zl);
      if (zc) out.push(zc);
      if (zr) out.push(zr);
    }
    return out;
  }

  function cancelBandAnims(el, innerEl, list) {
    if (el && el._bandAnim) { el._bandAnim.cancel(); el._bandAnim = null; }
    if (innerEl && innerEl._bandAnim) { innerEl._bandAnim.cancel(); innerEl._bandAnim = null; }
    for (const b of (list || [])) {
      if (b && b._bandShiftAnim) { b._bandShiftAnim.cancel(); b._bandShiftAnim = null; }
    }
  }

  function animateTopBand(el, innerSel, open) {
    if (!el) return;
    const token = (el._bandTok = (el._bandTok || 0) + 1);
    const below = belowElementsOf(el);
    const innerEl = innerSel ? $(innerSel, el) : el.firstElementChild;
    cancelBandAnims(el, innerEl, below);
    if (!motionOn() || typeof el.animate !== 'function') {
      el._closingBand = false;
      el.hidden = !open;
      placeGuides();
      requestAnimationFrame(() => updateSelLink(false));
      return;
    }
    if (open) {
      el._closingBand = false;
      const beforeTop = new Map(below.map(b => [b, b.getBoundingClientRect().top]));
      el.hidden = false;
      let maxShift = el.offsetHeight || 0;
      const dyMap = new Map();
      for (const b of below) {
        const dy = beforeTop.get(b) - b.getBoundingClientRect().top;
        dyMap.set(b, dy);
        if (Math.abs(dy) > maxShift) maxShift = Math.abs(dy);
      }
      const { dur, easing } = panelTiming(true, maxShift);
      if (!dur) { placeGuides(); requestAnimationFrame(() => updateSelLink(false)); return; }
      el._bandAnim = el.animate([
        { clipPath: 'inset(0% 0% 100% 0%)' },
        { clipPath: 'inset(0% 0% 0% 0%)' },
      ], { duration: dur, easing });
      if (innerEl && typeof innerEl.animate === 'function') {
        innerEl._bandAnim = innerEl.animate([
          { opacity: 0, offset: 0 },
          { opacity: 0, offset: 0.45 },
          { opacity: 1, offset: 1 },
        ], { duration: dur, easing });
      }
      for (const b of below) {
        const dy = dyMap.get(b) || 0;
        if (Math.abs(dy) >= 0.5 && typeof b.animate === 'function') {
          b._bandShiftAnim = b.animate([
            { transform: `translate3d(0,${dy.toFixed(2)}px,0)` },
            { transform: 'translate3d(0,0,0)' },
          ], { duration: dur, easing });
        }
      }
      el._bandAnim.onfinish = () => {
        if (token !== el._bandTok) return;
        el._bandAnim = null;
        placeGuides();
        updateSelLink(false);
      };
      placeGuides();
      requestAnimationFrame(() => updateSelLink(false));
    } else {
      if (el.hidden) return;
      el._closingBand = true;
      const curTop = new Map(below.map(b => [b, b.getBoundingClientRect().top]));
      const prevH = el.offsetHeight || 0;
      el.hidden = true;
      const targetTop = new Map(below.map(b => [b, b.getBoundingClientRect().top]));
      el.hidden = false;
      let maxShift = prevH;
      for (const b of below) {
        const dy = (targetTop.get(b) || 0) - (curTop.get(b) || 0);
        if (Math.abs(dy) > maxShift) maxShift = Math.abs(dy);
      }
      const { dur, easing } = panelTiming(false, maxShift);
      if (!dur) { el._closingBand = false; el.hidden = true; placeGuides(); return; }
      el._bandAnim = el.animate([
        { clipPath: 'inset(0% 0% 0% 0%)' },
        { clipPath: 'inset(0% 0% 100% 0%)' },
      ], { duration: dur, easing });
      if (innerEl && typeof innerEl.animate === 'function') {
        innerEl._bandAnim = innerEl.animate([
          { opacity: 1, offset: 0 },
          { opacity: 0, offset: 0.55 },
          { opacity: 0, offset: 1 },
        ], { duration: dur, easing });
      }
      for (const b of below) {
        const dy = targetTop.get(b) - curTop.get(b);
        if (Math.abs(dy) >= 0.5 && typeof b.animate === 'function') {
          b._bandShiftAnim = b.animate([
            { transform: 'translate3d(0,0,0)' },
            { transform: `translate3d(0,${dy.toFixed(2)}px,0)` },
          ], { duration: dur, easing });
        }
      }
      el._bandAnim.onfinish = () => {
        if (token !== el._bandTok) return;
        el._closingBand = false;
        el._bandAnim = null;
        cancelBandAnims(null, innerEl, below);
        el.hidden = true;
        placeGuides();
        updateSelLink(false);
      };
    }
  }

  function setCondOpen(open) {
    const next = !!open;
    if (condOpen === next) return;
    condOpen = next;
    const el = $('#cond'), b = $('#cond-sum');
    if (b) {
      b.setAttribute('aria-expanded', String(condOpen));
      const act = $('.act-t', b);
      if (act) act.textContent = cp(condOpen ? 'condCloseBtn' : 'condOpenBtn');
    }
    animateTopBand(el, '#cond-body', condOpen);
  }
  function setScopeOpen(open) {
    const next = !!open;
    if (scopeOpen === next) return;
    scopeOpen = next;
    const el = $('#scope'), b = $('#scope-tgl');
    if (b) b.setAttribute('aria-expanded', String(scopeOpen));
    animateTopBand(el, '.fade-band', scopeOpen);
  }

  function renderCond() {
    const mid = $('#th-mid');
    mid.innerHTML = `<div class="th-cond-line" id="cond-sum-t"></div>
      <div class="th-cond-btns" id="th-cond-btns">
        <span class="th-act-wrap" id="th-act-wrap">
          <button class="scope-tgl th-act-menu-btn" id="act-menu-btn" type="button" aria-expanded="false" aria-controls="th-act-btns">화면 도구 ${IC.chevD}</button>
          <span class="th-act-btns" id="th-act-btns" role="toolbar" aria-label="화면 조작"></span>
        </span>
        <i class="th-sep" id="th-act-sep" aria-hidden="true"></i>
        <button class="scope-tgl" id="cond-sum" type="button" aria-expanded="false" aria-controls="cond"><span class="act-t">${esc(cp('condOpenBtn'))}</span> ${IC.chevD}</button>
        <button class="scope-tgl peer-tgl" id="peer-tgl" type="button" data-peer-pop="1" aria-controls="help-pop" aria-expanded="false"><span id="peer-tgl-t"></span> ${IC.chevD}</button>
        <button class="scope-tgl" id="scope-tgl" type="button" aria-expanded="false" aria-controls="scope">${esc(cp('scopeBtn'))} ${IC.chevD}</button>${help('scope-band', cp('scopeTitle'))}
      </div>`;

    const el = $('#cond');
    el.setAttribute('aria-label', cp('condAria'));
    el.innerHTML = `<div class="cond-body" id="cond-body">
        <div class="cg" data-g="seg">
          <div class="cg-h">${esc(cp('condGroupSeg'))}</div>
          <div class="cf"><span class="lb">${esc(cp('condAge'))}</span><span data-slot="age"></span></div>
          <div class="cf"><span class="lb">${esc(cp('condSex'))}</span><span data-slot="sex"></span></div>
          <div class="cf"><label class="lb" for="c-since">${esc(cp('condSince'))}</label><select class="sel" id="c-since"></select></div>
          <div class="cf"><span class="lb" id="c-surg-l">${esc(cp('condSurgKind'))}</span><button type="button" class="sw" id="c-surg" role="switch" aria-checked="false" aria-describedby="c-surg-l"><i></i>${esc(cp('condSurgSwitch'))}</button></div>
        </div>
        <div class="cg" data-g="base">
          <div class="cg-h">${esc(cp('condGroupBase'))}</div>
          <div class="cf"><span class="lb">${esc(cp('condBase'))}${help('base-sel', cp('termBaseTitle'))}</span><span data-slot="base"></span></div>
          <div class="cf cf-peers"><span class="lb">${esc(cp('condPeers'))}</span><span class="ro" id="c-peers"></span></div>
          <div class="cf"><span class="lb">${esc(cp('condRenewal'))} <span class="hint">${esc(cp('condRenewalHint'))}</span></span><span data-slot="ren"></span></div>
        </div>
      </div>`;
    C.age = stepper({ label: cp('condAge'), value: st.age, min: 1, max: 100, unit: cp('condAgeUnit'), onChange: (v, keepCond) => set({ age: v }, { keepCond }) });
    C.sex = chevSel({ label: cp('condSex'), options: [{ v: 'M', t: cp('condMale') }, { v: 'F', t: cp('condFemale') }], value: st.sex, w: '56px', onChange: v => set({ sex: v }) });
    C.base = chevSel({ label: cp('condBase'), options: BASES.map(b => ({ v: b['종형ID'], t: b['이름'], title: vinfo(b['종형ID']) ? vinfo(b['종형ID'])['전체이름'] : '' })), value: st.base, w: '150px', onChange: v => set({ base: v }) });
    C.ren = chevSel({ label: cp('condRenewal'), options: [{ v: null, t: cp('condRenAll') }, { v: '갱신', t: cp('condRenRenew') }, { v: '비갱신', t: cp('condRenNon') }], value: st.renewal, w: '64px', onChange: v => set({ renewal: v }) });
    $('[data-slot="age"]', el).replaceWith(C.age);
    $('[data-slot="sex"]', el).replaceWith(C.sex);
    $('[data-slot="base"]', el).replaceWith(C.base);
    $('[data-slot="ren"]', el).replaceWith(C.ren);
    const sel = $('#c-since', el);
    sel.innerHTML = SINCE_OPTS.map((o, i) => `<option value="${i}">${esc(o.t)}</option>`).join('');
    sel.addEventListener('change', () => set({ since: SINCE_OPTS[+sel.value].v }));
    $('#c-surg', el).addEventListener('click', () => { if (st.since != null) set({ surg: !st.surg }); });
    $('#cond-sum').addEventListener('click', () => setCondOpen(!condOpen));
    $('#scope-tgl').addEventListener('click', () => setScopeOpen(!scopeOpen));
    syncCond();
  }

  function syncCond() {
    if (!C.age) return;
    C.age.set(st.age); C.sex.set(st.sex); C.base.set(st.base); C.ren.set(st.renewal);
    const sel = $('#c-since'); sel.value = String(SINCE_OPTS.findIndex(o => o.v === st.since));
    const sw = $('#c-surg'); sw.setAttribute('aria-checked', String(!!st.surg)); sw.disabled = st.since == null;
    sw.title = st.since == null ? cp('condSurgDisHint') : cp('condSurgHint');
    const base = S['기준별'][st.base];
    const pSet = new Set(activePeerOrgs());
    const peerVids = base ? (st.peerScope === 'all' ? base['맞붙는종형'] : base['맞붙는종형'].filter(v => pSet.has((vinfo(v) || {})['기관코드']))) : [];
    const peerOrgNames = [...new Set(peerVids.map(v => orgShort((vinfo(v) || {})['기관코드'])).filter(Boolean))];
    $('#c-peers').innerHTML = base ? `<span title="${esc(peerVids.map(vname).join(', '))}">${esc(peerNamesShort(peerOrgNames))}</span><span class="hint" style="margin-left:8px">${esc(cp('condPeersHint'))}</span>` : '';
    const pt = $('#peer-tgl-t');
    if (pt) pt.textContent = cp('peerBtnTpl', { s: peerScopeLabel() });
    const cs = $('#cond-sum-t');
    if (cs) cs.textContent = condSummary();
  }

  const STATE_IC = { '열림': IC.open, '일부 나이만 열림': IC.open, '닫힘': IC.lock, '심사로 확인': IC.check, '나이 자료 없음': IC.hatch, '질문 자료 없음': IC.hatch };
  function renderScope() {
    const el = $('#scope');
    el.setAttribute('aria-label', cp('scopeAria'));
    const base = S['기준별'][st.base];
    if (!base) { el.innerHTML = ''; return; }
    const r = base['범위'];
    const bi = vinfo(st.base);
    const pSet = new Set(activePeerOrgs());
    const relPeers = st.peerScope === 'all' ? r['상대'] : r['상대'].filter(p => pSet.has((vinfo(p['종형ID']) || {})['기관코드']));
    const restPeerNames = relPeers.slice(3).map(p => vname(p['종형ID'])).join(', ');
    const peers = relPeers.slice(0, 3).map(p => {
      const v = vinfo(p['종형ID']);
      const why = p['머리말'] != null ? S['글'][p['머리말']] : '';
      const sd = (why.split(` / ${cp('scopeDiffStruct')}: `)[1] || '');
      return `<span class="it"><span title="${esc(v ? v['전체이름'] : '')}">${esc(vname(p['종형ID']))}</span> <span class="d">${esc(v ? v['적용시작일'] : '')}</span>${p['구조다름'] ? ' ' + tag(cp('scopeDiffStruct'), sd ? cp('scopeDiffStruct') + ': ' + sd : cp('scopeDiffStructHint')) : ''}</span>`;
    }).join('') + (relPeers.length > 3 ? `<span class="it" title="${esc(restPeerNames)}" data-tip="${esc(restPeerNames)}">+${fmt(relPeers.length - 3)}</span>` : '') + (!relPeers.length ? `<span class="it">${esc(cp('condPeerNone'))}</span>` : '');
    let pairTot = r['비교쌍'], pairWait = r['뺀비교쌍'], pairScoped = true;
    if (st.peerScope !== 'all') {
      const sp = scopedPairs(st.base, pSet);
      if (sp) { pairTot = sp.total; pairWait = sp.wait; }
      else pairScoped = false;
    }
    const line1 = `<div class="scope-l"><span class="k">${esc(cp('scopeTitle'))}</span>
      <span class="it"><b style="font-weight:600" title="${esc(bi ? bi['전체이름'] : '')}">${esc(vname(st.base))}</b> <span class="d">${esc(bi ? bi['적용시작일'] : '')}</span></span>
      <span class="it" aria-label="${esc(cp('scopeVsAria'))}">${IC.arrow}</span>${peers}
      <span class="it">${esc(cp('scopePairTpl', { total: fmt(pairTot), wait: fmt(pairWait) }))}</span> ${pairScoped ? '' : fullScopeTag()}
      ${scope('base')}</div>`;
    const g = cellOf();
    let line2;
    if (!g.cell) {
      line2 = `<div class="scope-l"><span class="k">${esc(cp('scopeNowSeg'))}</span><span class="it">${esc(condSegOnly())}</span><span class="why">${esc(g.reason)}</span></div>`;
    } else {
      const c = g.cell;
      const shownOrgs = activeOrgs().filter(o => o in c['회사']);
      const restOrgStates = shownOrgs.slice(4).map(o => `${orgShort(o)} ${c['회사'][o]}`).join(', ');
      const states = shownOrgs.slice(0, 4).map(o => {
        const s = c['회사'][o];
        return `<span class="it">${esc(orgShort(o))} <span style="display:inline-flex;align-items:center;gap:4px">${STATE_IC[s] || ''}${esc(s)}</span></span>`;
      }).join('') + (shownOrgs.length > 4 ? `<span class="it" title="${esc(restOrgStates)}" data-tip="${esc(restOrgStates)}">+${fmt(shownOrgs.length - 4)}</span>` : '');
      const why = shownOrgs.slice(0, 4).map(o => stateWhy(o, c['회사'][o])).filter(Boolean);
      const rep = c['대표'];
      const repT = rep ? `<span class="it">${esc(cp('scopeOurRep'))} <b style="font-weight:600">${esc(vkind(rep))}</b></span>` : '';
      const act = rep && rep !== st.base ? `<span class="act live">${btn(cp('scopeSwitchBaseTpl', { target: josa(vkind(rep), '으로') }), { sm: true, attrs: `data-act="base-to" data-v="${esc(rep)}"` })}</span>` : '';
      const ns = [];
      if (c['보조']) ns.push(c['보조']);
      if (c['닫힌사유'] && c['닫힌사유'].length) ns.push(`${cp('scopeClosedWhy')}: ${c['닫힌사유'].join(', ')}`);
      line2 = `<div class="scope-l"><span class="k">${esc(cp('scopeNowSeg'))}</span>
        <span class="it">${esc(condSegOnly())}</span>
        <span class="it" style="display:inline-flex;align-items:center;gap:6px">${swatch(c['라벨'])}<b style="font-weight:600">${esc(c['라벨'])}</b>${ns.length ? `<span style="color:var(--ink-1)">(${esc(ns.join(', '))})</span>` : ''}</span>
        ${states}${repT}${why.concat(g.sexNote ? [g.sexNote] : []).map(w => `<span class="why">${esc(w)}</span>`).join('')}${act}</div>`;
    }
    if (!g.cell && g.sexNote) line2 += `<div class="scope-l"><span class="k">${esc(cp('scopeNoData'))}</span><span class="why">${esc(g.sexNote)}</span></div>`;
    if (!el._closingBand) el.hidden = !scopeOpen;
    el.innerHTML = fadeBand(line1 + line2);
  }

  // ---------- 다섯 고리 탭 수치(갱신 유형 및 비교 범위 교집합 정확히 반영, 숫자 창작 금지) ----------
  function lineOf(base, k) {
    return ((base && base['브리핑']) || []).find(x => x['줄'] === k) || null;
  }

  function ringTabMetrics(c) {
    const curC = c || ctx();
    const base = curC.base || S['기준별'][st.base];
    const pSet = new Set(curC.activePeerOrgs);
    const bGa = lineOf(base, '가'), bNa = lineOf(base, '나'), bDa = lineOf(base, '다'), bRa = lineOf(base, '라'), bMa = lineOf(base, '마');
    const vNa = (bNa && bNa['값']) || {}, vDa = (bDa && bDa['값']) || {}, vRa = (bRa && bRa['값']) || {}, vMa = (bMa && bMa['값']) || {};

    // 1. 고객군과 시장: 현재 갱신 선택 지도(mapOf(renewal))의 열린 칸 수 / 전체 칸 수
    const mCur = mapOf(curC.st.renewal);
    let gaTotal = 0, gaOnly = 0, gaBoth = 0;
    if (mCur && mCur['칸']) {
      mCur['칸'].forEach(row => row.forEach(cell => {
        gaTotal++;
        const cc = cellCounts(cell, curC.st);
        if (cc.oursOpen) {
          if (cc.openAny === 0) gaOnly++;
          else gaBoth++;
        }
      }));
    }
    const gaOpen = gaOnly + gaBoth;
    const revCnt = vNa['개정변동수'] != null ? vNa['개정변동수'] : ((S['개정변동'] && S['개정변동']['수'] && S['개정변동']['수']['전체']) || 0);

    // 2. 가입 관문: 자료의 관문차이수(관문차이상대코드가 있으면 교집합, 없으면 전체 값 + 전체 기준 배지)
    let daVal = vDa['관문차이수'] || 0;
    let daMax = Math.max(1, (base && base['범위'] && base['범위']['회사수']) || 1);
    let daFullBadge = false;
    if (curC.peerScope !== 'all') {
      if (Array.isArray(vDa['관문차이상대코드'])) {
        daVal = inScope(vDa['관문차이상대코드'], curC.st);
        daMax = Math.max(1, curC.activePeerOrgs.length);
      } else {
        daFullBadge = true;
      }
    }

    // 3. 담보 비교: 고른 비교 범위 안의 견준 쌍 / 공통 담보 쌍(보류요약.기관별 합산)
    let raCmp = vRa['견준쌍'] || 0, raTot = vRa['공통담보쌍'] || 0;
    if (curC.peerScope !== 'all') {
      const sp = scopedPairs(curC.baseId, pSet);
      if (sp) { raCmp = sp.cmp; raTot = sp.total; }
    }

    // 4. 영업 인사이트: 고른 비교 범위와 겹치는 포인트 건수(우체국 나음인 앞세울 강점만 금색 호)
    let maVal = vMa['전체수'] || 0, maGold = vMa['앞세울수'] || 0;
    if (curC.peerScope !== 'all' && base) {
      maVal = 0; maGold = 0;
      (base['포인트'] || []).forEach(id => {
        const p = S['포인트'][id];
        if (!p) return;
        if ((p['관련기관코드'] || []).some(o => pSet.has(o))) {
          maVal++;
          if (p['분류'] === '앞세울 강점') maGold++;
        }
      });
    }

    return {
      market: {
        id: 'market', name: TAB_NAME.market,
        val: gaOpen, denom: gaTotal, revCnt,
        numHTML: `${esc(fmt(gaOpen))}<small>/${esc(fmt(gaTotal))}</small>`,
        subText: cp('homeRevBadgeTpl', { n: fmt(revCnt) }),
        max: Math.max(1, gaTotal), segs: [{ v: gaOnly, cls: 'gold' }, { v: gaBoth, cls: '' }],
        flag: bGa && bGa['원문대조'] ? (bGa['원문대조글'] || cp('flagDefault')) : '',
        fullBadge: false,
      },
      gate: {
        id: 'gate', name: TAB_NAME.gate,
        val: daVal, denom: null,
        numHTML: `${esc(fmt(daVal))}`,
        subText: '',
        max: daMax, segs: [{ v: daVal, cls: '' }],
        flag: bDa && bDa['원문대조'] ? (bDa['원문대조글'] || cp('flagDefault')) : '',
        fullBadge: daFullBadge,
      },
      cover: {
        id: 'cover', name: TAB_NAME.cover,
        val: raCmp, denom: raTot,
        numHTML: `${esc(fmt(raCmp))}<small>/${esc(fmt(raTot))}</small>`,
        subText: '',
        max: Math.max(1, raTot || 1), segs: [{ v: raCmp, cls: '' }],
        flag: bRa && bRa['원문대조'] ? (bRa['원문대조글'] || cp('flagDefault')) : '',
        fullBadge: false,
      },
      insight: {
        id: 'insight', name: TAB_NAME.insight,
        val: maVal, denom: null,
        numHTML: `${esc(fmt(maVal))}`,
        subText: '',
        max: Math.max(1, maVal || 1), segs: [{ v: maGold, cls: 'gold' }, { v: Math.max(0, maVal - maGold), cls: '' }],
        flag: bMa && bMa['원문대조'] ? (bMa['원문대조글'] || cp('flagDefault')) : '',
        fullBadge: false,
      },
      graph: {
        id: 'graph', name: TAB_NAME.graph,
        val: null, denom: null,
        numHTML: '',
        subText: '',
        isGraph: true,
        max: 1, segs: [],
        flag: '',
        fullBadge: false,
      },
    };
  }

  function graphGlyphSVG() {
    return `<svg viewBox="-24 -24 48 48" aria-hidden="true" focusable="false">
      <circle class="rt-trk" r="20" fill="none" stroke-width="1"/>
      <path class="rt-glyph" d="M-10 4L-2 -7L10 -3M-2 -7L3 8L-10 4M3 8L11 6"/>
      <rect class="rt-glyph-dot" x="-12.5" y="1.5" width="5" height="5"/>
      <rect class="rt-glyph-dot" x="-4.5" y="-9.5" width="5" height="5"/>
      <rect class="rt-glyph-dot" x="7.5" y="-5.5" width="5" height="5"/>
      <rect class="rt-glyph-dot" x="0.5" y="5.5" width="5" height="5"/>
      <rect class="rt-glyph-dot" x="8.5" y="3.5" width="4.5" height="4.5"/>
    </svg>`;
  }

  function rtabRingSVG(m, withDiag) {
    if (m.isGraph) return graphGlyphSVG();
    const r = 34;
    const arcD = `M 0 -${r} A ${r} ${r} 0 1 1 -0.01 -${r}`;
    const max = Math.max(0.0001, m.max || 1);
    let cum = 0;
    const validSegs = (m.segs || []).filter(s => s.v > 0);
    const segSpecs = validSegs.map(s => {
      cum = Math.min(1, cum + s.v / max);
      const endPct = +(cum * 100).toFixed(2);
      const off = +(100 - endPct).toFixed(2);
      return { cls: s.cls || '', off };
    });
    // 뒤쪽 누적 호부터 먼저 깔고 앞쪽 주 호를 위에 얹어 stroke-dashoffset 만으로 전환한다(4-3)
    const arcs = segSpecs.slice().reverse().map((sp, revIdx) => {
      const sw = revIdx === segSpecs.length - 1 && segSpecs.length > 1 ? 4.5 : 4.4;
      return `<path class="rt-arc${sp.cls ? ' ' + sp.cls : ''}" d="${arcD}" pathLength="100" fill="none" stroke-width="${sw}" stroke-dasharray="100 200" stroke-dashoffset="${sp.off}" data-doff="${sp.off}"/>`;
    }).join('');
    const f = cum;
    let ticks = '';
    if (f < 0.999) {
      const N = 24, r1 = r - 2.6, r2 = r + 2.6;
      const ls = [];
      for (let i = 0; i < N; i++) {
        if (i / N < f - 0.004) continue;
        const a = (i / N) * 2 * Math.PI - Math.PI / 2;
        ls.push(`<line x1="${(r1 * Math.cos(a)).toFixed(1)}" y1="${(r1 * Math.sin(a)).toFixed(1)}" x2="${(r2 * Math.cos(a)).toFixed(1)}" y2="${(r2 * Math.sin(a)).toFixed(1)}" stroke-width="1"/>`);
      }
      ticks = `<g class="rt-tks">${ls.join('')}</g>`;
    }
    const diag = withDiag
      ? '<g class="rt-tks" stroke-width="1.1"><line x1="-36" y1="-36" x2="-30" y2="-30"/><line x1="36" y1="-36" x2="30" y2="-30"/><line x1="-36" y1="36" x2="-30" y2="30"/><line x1="36" y1="36" x2="30" y2="30"/></g>'
      : '';
    return `<svg viewBox="-42 -42 84 84" aria-hidden="true" focusable="false">
      ${diag}
      <circle class="rt-trk" r="39" fill="none" stroke-width="1"/>
      <circle class="rt-disc" r="28"/>
      <circle class="rt-trk" r="${r}" fill="none" stroke-width="1.2"/>
      ${ticks}${arcs}
    </svg>`;
  }

  function miniRingSVG(v, max, cls) {
    const r = 15;
    const arcD = `M 0 -${r} A ${r} ${r} 0 1 1 -0.01 -${r}`;
    const f = max > 0 ? Math.max(0, Math.min(1, v / max)) : 0;
    const off = +(100 - f * 100).toFixed(2);
    return `<svg viewBox="-20 -20 40 40" aria-hidden="true" focusable="false">
      <circle class="rt-trk" r="${r}" fill="none" stroke-width="1.8"/>
      ${f > 0 ? `<path class="rt-arc${cls ? ' ' + cls : ''}" d="${arcD}" pathLength="100" fill="none" stroke-width="2.8" stroke-dasharray="100 200" stroke-dashoffset="${off}"/>` : ''}
    </svg>`;
  }
  UI.miniRingSVG = miniRingSVG;
  UI.graphGlyphSVG = graphGlyphSVG;

  // ---------- 화면 간 연속 전환(기준축 다리, 작은 고리 <-> 머리 큰 고리, 고른 탭 면 미끄러짐) ----------
  let axisBridgeToken = 0;
  let ringFlyEl = null;

  function findVisibleMainAxis(tabId) {
    const scopeRoot = tabId === 'brief' ? $('#home-panel') : (viewOf(tabId) || $('#z-center'));
    if (!scopeRoot || scopeRoot.hidden) return null;
    const el = $('[data-main-axis]', scopeRoot)
      || $('.hm-axis-wrap, .cv-stage-axis, .cv-axis-line, .gtf-axis-head, .mk-thead, .gr-head-bar, .ins-top-bar', scopeRoot);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    if (r.width < 10) return null;
    return { el, left: Math.round(r.left), width: Math.round(r.width), y: Math.round(r.bottom - 2) };
  }

  function snapScreenTransition(fromTab, toTab) {
    const out = { fromTab, toTab, axis: null, pill: null, bigRing: null, bigRingHTML: '', srcRing: null };
    out.axis = findVisibleMainAxis(fromTab);
    const nav = $('#rtabs');
    if (nav && !nav.hidden) {
      const act = $('.rtab[aria-selected="true"]', nav);
      if (act) out.pill = { left: act.offsetLeft, width: act.offsetWidth };
      if (toTab !== 'brief') {
        const nextBtn = $('#tab-' + toTab + ' .rt-ring', nav);
        if (nextBtn) {
          const r = nextBtn.getBoundingClientRect();
          if (r.width > 4) out.srcRing = r;
        }
      }
    } else if (fromTab === 'brief' && toTab !== 'brief') {
      const hm = $(`#home-panel #tab-${toTab} .hm-head`) || $(`#home-panel #tab-${toTab}`);
      if (hm) {
        const r = hm.getBoundingClientRect();
        if (r.width > 4) out.srcRing = { left: r.left, top: r.top, width: Math.min(84, r.width), height: Math.min(84, r.height) };
      }
    }
    const thRing = $('#th-total .tht-ring');
    if (thRing && !$('#th-total').hidden) {
      const r = thRing.getBoundingClientRect();
      if (r.width > 4) {
        out.bigRing = r;
        out.bigRingHTML = thRing.outerHTML;
      }
    }
    return out;
  }

  function playAxisBridge(prevAxis, nextAxis) {
    const bridge = $('#axis-bridge');
    if (!bridge) return;
    if (!motionOn()) {
      document.body.classList.remove('axis-bridging');
      bridge.hidden = true;
      return;
    }
    if (prevAxis && nextAxis && Math.abs(prevAxis.y - nextAxis.y) >= 1) {
      const token = ++axisBridgeToken;
      const vw = Math.max(1, innerWidth);
      const dur = Math.round(380 * motionScale());
      bridge.hidden = false;
      document.body.classList.add('axis-bridging');
      if (bridge._anim) bridge._anim.cancel();
      const t0 = `translate3d(${prevAxis.left}px,${prevAxis.y}px,0) scaleX(${(prevAxis.width / vw).toFixed(4)})`;
      const t1 = `translate3d(${nextAxis.left}px,${nextAxis.y}px,0) scaleX(${(nextAxis.width / vw).toFixed(4)})`;
      bridge.style.transform = t1;
      bridge._anim = bridge.animate([{ transform: t0 }, { transform: t1 }], {
        duration: dur,
        easing: 'cubic-bezier(0.65, 0, 0.35, 1)',
      });
      bridge._anim.onfinish = () => {
        if (token !== axisBridgeToken) return;
        document.body.classList.remove('axis-bridging');
        bridge.hidden = true;
      };
    } else if (nextAxis && nextAxis.el) {
      document.body.classList.remove('axis-bridging');
      bridge.hidden = true;
      nextAxis.el.classList.remove('axis-draw');
      void nextAxis.el.offsetWidth;
      nextAxis.el.classList.add('axis-draw');
    }
  }

  function flipElement(el, fromRect, durMs, easing) {
    if (!el || !fromRect || !motionOn() || typeof el.animate !== 'function') return;
    const toRect = el.getBoundingClientRect();
    if (toRect.width < 2 || toRect.height < 2) return;
    const dx = (fromRect.left + fromRect.width / 2) - (toRect.left + toRect.width / 2);
    const dy = (fromRect.top + fromRect.height / 2) - (toRect.top + toRect.height / 2);
    const sx = Math.max(0.35, Math.min(2.4, fromRect.width / toRect.width));
    const sy = Math.max(0.35, Math.min(2.4, fromRect.height / toRect.height));
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1 && Math.abs(sx - 1) < 0.03) return;
    if (el._flipAnim) el._flipAnim.cancel();
    el._flipAnim = el.animate([
      { transform: `translate3d(${dx.toFixed(1)}px,${dy.toFixed(1)}px,0) scale(${sx.toFixed(3)},${sy.toFixed(3)})` },
      { transform: 'translate3d(0,0,0) scale(1,1)' },
    ], {
      duration: Math.max(80, Math.round(durMs * motionScale())),
      easing: easing || 'cubic-bezier(0.16, 1, 0.3, 1)',
    });
  }

  function drawHeaderRingArcs(root) {
    if (!motionOn()) return;
    for (const c of $$('.rt-arc[data-doff]', root)) {
      const doff = c.dataset.doff;
      c.style.transition = 'none';
      c.setAttribute('stroke-dashoffset', '100');
      void c.getBoundingClientRect();
      c.style.transition = '';
      c.setAttribute('stroke-dashoffset', doff);
    }
  }

  function playReturnRingToHome(snap) {
    if (!motionOn() || !snap || !snap.bigRing || !snap.bigRingHTML) return;
    const target = $(`#home-panel #tab-${snap.fromTab} .hm-head`) || $(`#home-panel #tab-${snap.fromTab}`);
    if (!target) return;
    const tr = target.getBoundingClientRect();
    if (tr.width < 4) return;
    if (!ringFlyEl) {
      ringFlyEl = document.createElement('div');
      ringFlyEl.style.cssText = 'position:fixed;left:0;top:0;pointer-events:none;z-index:29;transform-origin:top left';
      document.body.appendChild(ringFlyEl);
    }
    ringFlyEl.innerHTML = snap.bigRingHTML;
    ringFlyEl.hidden = false;
    const br = snap.bigRing;
    const sc = Math.max(0.45, Math.min(1, 52 / Math.max(1, br.height)));
    if (ringFlyEl._anim) ringFlyEl._anim.cancel();
    ringFlyEl._anim = ringFlyEl.animate([
      { transform: `translate3d(${br.left.toFixed(1)}px,${br.top.toFixed(1)}px,0) scale(1)`, opacity: 0.95 },
      { transform: `translate3d(${tr.left.toFixed(1)}px,${tr.top.toFixed(1)}px,0) scale(${sc.toFixed(3)})`, opacity: 0 },
    ], {
      duration: Math.max(90, Math.round(320 * motionScale())),
      easing: 'cubic-bezier(0.65, 0, 0.35, 1)',
    });
    ringFlyEl._anim.onfinish = () => { if (ringFlyEl) { ringFlyEl.hidden = true; ringFlyEl.innerHTML = ''; } };
  }

  function syncRtabsCue(scrollActive) {
    const nav = $('#rtabs');
    const cueL = $('#rt-cue-l'), cueR = $('#rt-cue-r');
    if (!nav || nav.hidden) {
      if (cueL) cueL.hidden = true;
      if (cueR) cueR.hidden = true;
      return;
    }
    if (scrollActive) {
      const act = $('.rtab[aria-selected="true"]', nav);
      if (act && nav.scrollWidth > nav.clientWidth + 4) {
        const maxLeft = Math.max(0, nav.scrollWidth - nav.clientWidth);
        nav.scrollLeft = Math.max(0, Math.min(maxLeft, Math.round(act.offsetLeft - (nav.clientWidth - act.offsetWidth) / 2)));
      }
    }
    const actPill = $('.rtab[aria-selected="true"]', nav);
    const pill = $('#rtab-bg', nav);
    if (pill && actPill) {
      const toX = actPill.offsetLeft, toS = Math.max(0.1, actPill.offsetWidth / 100);
      pill.style.transform = `translate3d(${toX}px,0,0) scaleX(${toS.toFixed(4)})`;
    }
    const over = nav.scrollWidth > nav.clientWidth + 4;
    const moreL = over && nav.scrollLeft > 4;
    const moreR = over && (nav.scrollLeft + nav.clientWidth < nav.scrollWidth - 4);
    nav.classList.toggle('has-more-l', moreL);
    nav.classList.toggle('has-more-r', moreR);
    if (cueL) cueL.hidden = !moreL;
    if (cueR) cueR.hidden = !moreR;
  }

  function renderRingTabs(c, snap) {
    const nav = $('#rtabs');
    const wrap = $('#rtabs-wrap');
    const thTotal = $('#th-total');
    if (!nav) return;
    const isHome = st.tab === 'brief';
    if (isHome) {
      nav.hidden = true;
      if (wrap) wrap.hidden = true;
      nav.classList.remove('has-pill', 'has-more-l', 'has-more-r');
      nav.innerHTML = '';
      if (thTotal) { thTotal.hidden = true; thTotal.innerHTML = ''; }
      syncRtabsCue(false);
      lastRenderedTab = 'brief';
      return;
    }
    const enteredFromHome = lastRenderedTab === 'brief' && motionOn();
    lastRenderedTab = st.tab;
    if (wrap) wrap.hidden = false;
    nav.hidden = false;
    if (enteredFromHome) {
      nav.classList.remove('from-home');
      void nav.offsetWidth;
      nav.classList.add('from-home');
    }
    const metrics = ringTabMetrics(c || ctx());
    const pillHTML = '<i class="rtab-bg" id="rtab-bg" aria-hidden="true"></i>';
    const homeBtn = `<button class="rtab rtab-home" type="button" role="tab" id="tab-brief" data-rtab="brief" aria-selected="false" tabindex="-1">${IC.chevL}<span>${esc(cp('homePathRoot'))}</span></button>`;
    const tabsHTML = SCREEN_IDS.map(id => {
      const m = metrics[id];
      const on = st.tab === id;
      const badge = m.fullBadge ? ` <span class="tag" title="${esc(cp('fullScopeHint'))}">${esc(cp('fullScopeBadge'))}</span>` : '';
      const sub = m.subText ? `<span class="rt-sub">${esc(m.subText)}</span>` : '';
      return `<button class="rtab" type="button" role="tab" id="tab-${id}" data-rtab="${id}" aria-selected="${on}" tabindex="${on ? 0 : -1}">
        <span class="rt-ring">${m.flag ? flag(m.flag) : ''}${rtabRingSVG(m, false)}${m.numHTML ? `<span class="rt-num num">${m.numHTML}</span>` : ''}</span>
        <span class="rt-txt"><span class="rt-name"><span>${esc(m.name)}</span>${badge}</span>${sub}</span>
      </button>`;
    }).join('');
    nav.classList.add('has-pill');
    nav.innerHTML = pillHTML + homeBtn + tabsHTML;

    const act = $('.rtab[aria-selected="true"]', nav);
    syncRtabsCue(true);
    const pill = $('#rtab-bg', nav);
    if (pill && act) {
      const toX = act.offsetLeft, toS = Math.max(0.1, act.offsetWidth / 100);
      pill.style.transform = `translate3d(${toX}px,0,0) scaleX(${toS.toFixed(4)})`;
      if (snap && snap.pill && motionOn() && typeof pill.animate === 'function' && (Math.abs(snap.pill.left - toX) > 1 || Math.abs(snap.pill.width - act.offsetWidth) > 1)) {
        const fromS = Math.max(0.1, snap.pill.width / 100);
        pill.animate([
          { transform: `translate3d(${snap.pill.left}px,0,0) scaleX(${fromS.toFixed(4)})` },
          { transform: `translate3d(${toX}px,0,0) scaleX(${toS.toFixed(4)})` },
        ], {
          duration: Math.max(90, Math.round(280 * motionScale())),
          easing: 'cubic-bezier(0.65, 0, 0.35, 1)',
        });
      }
    }

    if (thTotal) {
      const curM = metrics[st.tab] || metrics.market;
      thTotal.hidden = false;
      thTotal.innerHTML = `<div class="tht-ring">${rtabRingSVG(curM, true)}${curM.numHTML ? `<span class="tht-val num">${curM.numHTML}</span>` : ''}</div>`;
      if (snap && motionOn()) {
        const thRing = $('.tht-ring', thTotal);
        if (thRing && snap.srcRing) flipElement(thRing, snap.srcRing, 420, 'cubic-bezier(0.16, 1, 0.3, 1)');
        drawHeaderRingArcs(thTotal);
        if (snap.fromTab && snap.fromTab !== 'brief' && snap.fromTab !== st.tab && snap.bigRing) {
          const prevSmall = $(`#tab-${snap.fromTab} .rt-ring`, nav);
          if (prevSmall) flipElement(prevSmall, snap.bigRing, 320, 'cubic-bezier(0.65, 0, 0.35, 1)');
        }
      }
    }
  }

  // ---------- 제목, 경로(#lpath), 상단 화면 단추(#th-act-btns) ----------
  function syncHeaderAndPath(c) {
    const curC = c || ctx();
    const ttl = $('#th-title');
    if (ttl) ttl.textContent = TAB_NAME[st.tab] || cp('homeTitle');
    const nav = $('#lpath');
    if (!nav) return;
    if (st.tab === 'brief') {
      nav.innerHTML = `<span class="lp-cur">${esc(cp('homePathRoot'))}</span>`;
      return;
    }
    const t = tabs[st.tab];
    let parts = [cp('homePathRoot'), TAB_NAME[st.tab]];
    if (t && t.path) {
      try {
        const custom = t.path(curC);
        if (Array.isArray(custom) && custom.length) parts = [cp('homePathRoot')].concat(custom);
      } catch (e) { console.error(e); }
    } else if (st.sel[st.tab] != null) {
      const evT = $('#ev-t') ? $('#ev-t').textContent : String(st.sel[st.tab]);
      if (evT) parts.push(evT);
    }
    nav.innerHTML = parts.map((label, idx) => {
      const last = idx === parts.length - 1;
      if (last) return `<span class="lp-cur">${esc(label)}</span>`;
      return `<button type="button" class="lp-b" data-path-idx="${idx}">${esc(label)}</button><span class="lp-sep" aria-hidden="true">&gt;</span>`;
    }).join('');
  }

  function renderActBar(c) {
    const box = $('#th-act-btns');
    const sep = $('#th-act-sep');
    if (!box) return;
    const curC = c || ctx();
    const btns = [];
    if (st.tab !== 'brief') {
      btns.push(btn(cp('actBack'), { sm: true, ghost: true, icon: 'chevL', attrs: 'id="act-back" data-layer-up="1"' }));
    }
    const t = tabs[st.tab];
    if (t && typeof t.actions === 'function') {
      try {
        const extra = t.actions(curC);
        if (extra) btns.push(extra);
      } catch (e) { console.error(e); }
    }
    btns.push(btn(cp('actCopySum'), { sm: true, ghost: true, icon: 'copy', attrs: 'id="act-copy" data-act="copy-summary"' }));
    const legKey = LEGENDS[st.tab] ? st.tab : 'verdict';
    btns.push(legendBtn(legKey, cp('legendBtn')));
    box.innerHTML = btns.join('');
    if (sep) sep.hidden = btns.length === 0;
  }

  // ---------- 본문 무대 렌더링 ----------
  function ensureLegacySections() {
    const center = $('#z-center');
    for (const id of SCREEN_IDS) {
      if ($('#view-' + id)) continue;
      const sec = document.createElement('section');
      sec.className = 'view'; sec.id = 'view-' + id; sec.hidden = true;
      sec.dataset.tab = id;
      sec.innerHTML = '<div class="vhead-aside" hidden></div><div class="vbody"></div>';
      center.appendChild(sec);
    }
  }
  function viewOf(id) { return document.getElementById('view-' + id); }

  function renderLegacyLeft(id, sec) {
    const left = $('#z-left');
    const sections = $$('section[id]', sec).filter(s => $('h2', s));
    if (!sections.length) {
      left.innerHTML = `<div class="zl-head"><span class="zl-k">${esc(TAB_NAME[id])}</span></div>`;
      return;
    }
    left.innerHTML = `<div class="zl-head"><span class="zl-k">${esc(cp('zlSecTitle'))}</span></div>
      <div class="zl-list" role="listbox" aria-label="${esc(TAB_NAME[id])}">
        ${sections.slice(0, 6).map((s, idx) => {
          const h2 = $('h2', s);
          const nm = h2 ? h2.textContent.replace(/^0\d\s*/, '').replace(/\s*\?\s*$/, '').trim() : s.id;
          return `<button type="button" class="zl-item${idx === 0 ? ' is-on' : ''}" data-jump-sec="${esc(s.id)}">
            <span class="zl-ring">${miniRingSVG(1, 1, '')}<span class="zl-n num">0${idx + 1}</span></span>
            <span class="zl-t">${esc(nm)}</span>
          </button>`;
        }).join('')}
      </div>`;
  }

  function syncLegacyLegend(id) {
    const t = tabs[id];
    if (!t || !t.evidence || LEGENDS[id]) return;
    registerLegend(id, 'legendVerdictTitle', c => {
      const spec = t.evidence(c);
      return spec && spec.body ? spec.body : legendHTML();
    });
  }

  function boardLayoutFor(id) {
    const t = tabs[id];
    if (t && t.layout) return t.layout;
    if (id === 'cover') return 'band';
    if (id === 'market' || id === 'gate') return 'side';
    return 'three';
  }

  let activeRenderedTab = 'brief';

  function applyBgParallax(tabId) {
    if (!motionRich()) {
      document.documentElement.style.setProperty('--bg-px', '0px');
      return;
    }
    const idx = Math.max(0, TAB_IDS.indexOf(tabId));
    document.documentElement.style.setProperty('--bg-px', `${(idx - 1) * -12}px`);
  }

  function renderActiveScreen(c, why) {
    const curC = c || ctx();
    const isTabSwitch = why === 'tab' && booted && activeRenderedTab !== st.tab;
    const snap = isTabSwitch ? snapScreenTransition(activeRenderedTab, st.tab) : null;
    activeRenderedTab = st.tab;
    applyBgParallax(st.tab);
    renderRingTabs(curC, snap);
    const isHome = st.tab === 'brief';
    const homePanel = $('#home-panel');
    const board = $('#board');
    homePanel.hidden = !isHome;
    board.hidden = isHome;

    if (isHome) {
      hideEv();
      clearSelLink();
      hideSelGlide();
      board.classList.remove('has-sel');
      const tb = tabs.brief;
      if (tb && tb.renderHome) tb.renderHome(homePanel, curC, why || 'render');
      syncHeaderAndPath(curC);
      renderActBar(curC);
      placeGuides();
      if (snap) {
        if (motionOn() && typeof homePanel.animate === 'function') {
          const { dur, easing } = panelTiming(true);
          if (dur > 0) homePanel.animate([{ opacity: 0 }, { opacity: 1 }], { duration: dur, easing });
        }
        playAxisBridge(snap.axis, findVisibleMainAxis('brief'));
        playReturnRingToHome(snap);
      }
      return;
    }

    if (!isHome && homePanel.innerHTML) homePanel.innerHTML = '';
    const lay = boardLayoutFor(st.tab);
    board.dataset.layout = lay;
    board.dataset.tab = st.tab;
    const zl = $('#z-left');
    if (zl) zl.hidden = lay !== 'three';

    ensureLegacySections();
    for (const x of SCREEN_IDS) {
      const v = viewOf(x);
      if (v) v.hidden = x !== st.tab;
    }

    const id = st.tab;
    const t = tabs[id];
    const sec = viewOf(id);
    const body = sec ? $('.vbody', sec) : $('#z-center');
    const aside = sec ? $('.vhead-aside', sec) : null;
    if (!t) {
      if (zl) zl.innerHTML = '';
      if (body) body.innerHTML = `<div class="placeholder">${esc(cp('tabMissing'))}</div>`;
    } else if (typeof t.renderStage === 'function') {
      try {
        t.renderStage(body, Object.assign({}, curC, { why: why || 'render', view: sec }));
      } catch (e) {
        console.error(e);
        body.innerHTML = `<div class="placeholder">${esc(cp('tabErrorPrefix') + e.message)}</div>`;
      }
      t._dirty = false;
      t._drawn = true;
    } else if (typeof t.renderZones === 'function') {
      try {
        t.renderZones({ left: zl, center: body, ctx: Object.assign({}, curC, { why: why || 'render', view: sec }) });
      } catch (e) {
        console.error(e);
        body.innerHTML = `<div class="placeholder">${esc(cp('tabErrorPrefix') + e.message)}</div>`;
      }
      t._dirty = false;
      t._drawn = true;
    } else {
      syncLegacyLegend(id);
      if (why === 'change' || t._dirty || !t._drawn) {
        let done = false;
        if (why === 'change' && t.update && t._drawn) {
          try { done = t.update(body, Object.assign({}, curC, { aside, view: sec })) === true; } catch (e) { console.error(e); }
        }
        if (!done) {
          try { t.render(body, Object.assign({}, curC, { aside, view: sec, why: why || 'render' })); } catch (e) { console.error(e); }
        }
        t._dirty = false;
        t._drawn = true;
      }
      if (lay === 'three') renderLegacyLeft(id, sec);
    }

    if (why === 'tab' && t && t.enter) {
      try { t.enter(body, curC); } catch (e) { console.error(e); }
    }
    if (sec) drawRings(sec);
    applySelectionState(false, curC);
    renderActBar(curC);
    placeGuides();
    if (snap) {
      if (motionOn()) {
        const { dur, easing } = panelTiming(true);
        if (dur > 0) {
          if (sec && typeof sec.animate === 'function') sec.animate([{ opacity: 0 }, { opacity: 1 }], { duration: dur, easing });
          const zr = $('#z-right');
          if (zr && !zr.hidden && typeof zr.animate === 'function') zr.animate([{ opacity: 0 }, { opacity: 1 }], { duration: dur, easing });
          if (zl && !zl.hidden && typeof zl.animate === 'function') zl.animate([{ opacity: 0 }, { opacity: 1 }], { duration: dur, easing });
        }
      }
      playAxisBridge(snap.axis, findVisibleMainAxis(id));
    }
  }

  // ---------- 읽기 영역(.z-right), 고른 표지 미끄러짐(#sel-glide), 1px 연결선(#sel-link) ----------
  const EV = { open: false };
  let selGlideToken = 0;

  function syncRightScrollCue() {
    const body = $('#ev-body'), more = $('#zr-more');
    if (!body || !more) return;
    const over = body.scrollHeight - body.clientHeight > 6 && body.scrollTop + body.clientHeight < body.scrollHeight - 6;
    more.hidden = !over;
  }

  function hideSelGlide() {
    const g = $('#sel-glide');
    if (!g) return;
    selGlideToken++;
    if (g._anim) g._anim.cancel();
    g.hidden = true;
  }

  function measureSelBox(tabId) {
    const id = tabId || st.tab;
    if (id === 'brief' || st.sel[id] == null) return null;
    const root = viewOf(id) || $('#z-center');
    const selEl = root && ($('[data-sel-anchor]', root) || $('.is-sel', root));
    if (!selEl) return null;
    const target = selEl.querySelector('[data-aim-box]') || selEl.querySelector('[data-link-pt]') || selEl;
    const r = target.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return null;
    return {
      key: String(st.sel[id]),
      left: r.left,
      top: r.top,
      width: r.width,
      height: r.height,
      shape: selEl.dataset.aim === 'circle' ? 'circle' : 'rect',
    };
  }

  function playSelGlide(prevBox, nextBox) {
    const g = $('#sel-glide'), board = $('#board');
    if (!g || !board || board.hidden || !prevBox || !nextBox || !motionOn() || typeof g.animate !== 'function') {
      hideSelGlide();
      return;
    }
    if (prevBox.key === nextBox.key) return;
    const bBox = board.getBoundingClientRect();
    const token = ++selGlideToken;
    const w1 = Math.max(6, Math.round(nextBox.width));
    const h1 = Math.max(6, Math.round(nextBox.height));
    const sx0 = Math.max(0.25, prevBox.width / w1);
    const sy0 = Math.max(0.25, prevBox.height / h1);
    const x0 = prevBox.left - bBox.left;
    const y0 = prevBox.top - bBox.top;
    const x1 = nextBox.left - bBox.left;
    const y1 = nextBox.top - bBox.top;
    g.dataset.shape = nextBox.shape;
    g.style.width = w1 + 'px';
    g.style.height = h1 + 'px';
    g.style.transform = `translate3d(${x1.toFixed(1)}px,${y1.toFixed(1)}px,0)`;
    g.hidden = false;
    if (g._anim) g._anim.cancel();
    g._anim = g.animate([
      { transform: `translate3d(${x0.toFixed(1)}px,${y0.toFixed(1)}px,0) scale(${sx0.toFixed(3)},${sy0.toFixed(3)})`, opacity: 0.96 },
      { transform: `translate3d(${x1.toFixed(1)}px,${y1.toFixed(1)}px,0) scale(1,1)`, opacity: 0.96 },
    ], {
      duration: Math.max(80, Math.round(220 * motionScale())),
      easing: 'cubic-bezier(0.65, 0, 0.35, 1)',
    });
    g._anim.onfinish = () => {
      if (token !== selGlideToken) return;
      g.hidden = true;
    };
  }

  function clearSelLink() {
    const p = $('#sel-link-p'), dot = $('#sel-link-dot');
    if (p) { if (p._anim) p._anim.cancel(); p.setAttribute('d', ''); }
    if (dot) { dot.setAttribute('hidden', ''); dot.style.display = 'none'; }
  }

  function updateSelLink(drawLine) {
    const p = $('#sel-link-p'), dot = $('#sel-link-dot'), board = $('#board'), zr = $('#z-right');
    if (!p || !board || board.hidden || !zr || !zr.classList.contains('is-picked') || mode() === 'sheet') {
      clearSelLink();
      return;
    }
    const root = viewOf(st.tab) || $('#z-center');
    const selEl = root && ($('[data-sel-anchor]', root) || $('.is-sel', root));
    if (!selEl) { clearSelLink(); return; }
    const anchor = selEl.querySelector('[data-link-pt]') || selEl.querySelector('[data-aim-box]') || selEl;
    const zc = $('#z-center');
    const bBox = board.getBoundingClientRect();
    const sBox = anchor.getBoundingClientRect();
    const rBox = zr.getBoundingClientRect();
    const zcBox = zc ? zc.getBoundingClientRect() : sBox;
    if (!sBox.width || !sBox.height || !rBox.width || !rBox.height) { clearSelLink(); return; }
    const lay = board.dataset.layout || 'side';
    let d = '', dx = 0, dy = 0;
    if (lay === 'band') {
      const sx = Math.round(sBox.left + sBox.width / 2 - bBox.left);
      const sy = Math.round(sBox.bottom - bBox.top);
      const ey = Math.round(rBox.top - bBox.top);
      if (ey > sy - 4) {
        d = `M${sx} ${sy}V${ey}`;
        dx = sx; dy = sy;
      }
    } else {
      const ex = Math.round(rBox.left - bBox.left);
      const ey = Math.round(Math.max(rBox.top + 22, Math.min(rBox.bottom - 22, sBox.top + sBox.height / 2)) - bBox.top);
      const zcRight = Math.round(zcBox.right - bBox.left);
      const gutterX = Math.max(zcRight + 2, Math.min(ex - 4, Math.round((zcRight + ex) / 2)));
      const fullSelBox = selEl.getBoundingClientRect();
      const midY = sBox.top + sBox.height / 2;
      // 같은 줄 오른쪽에 다른 도형이나 글자가 있으면 줄 사이 빈 틈으로 내려서 꺾어 보낸다(요청 30의 2-1)
      let blockedRight = false;
      const track = selEl.closest('.mk-track, .gtf-track');
      if (track) {
        let sib = selEl.nextElementSibling;
        while (sib) {
          if (sib.matches('[data-pick], .mk-ring, .gtf-cell')) { blockedRight = true; break; }
          sib = sib.nextElementSibling;
        }
      } else {
        for (const other of $$('[data-pick], [data-gr-node]', root)) {
          if (other === selEl || selEl.contains(other) || other.contains(selEl)) continue;
          const ob = other.getBoundingClientRect();
          if (ob.width < 2 || ob.height < 2) continue;
          if (ob.left >= fullSelBox.right - 2 && midY >= ob.top - 4 && midY <= ob.bottom + 4) {
            blockedRight = true;
            break;
          }
        }
      }
      if (blockedRight) {
        const cx = Math.round(sBox.left + sBox.width / 2 - bBox.left);
        const by = Math.round(sBox.bottom - bBox.top);
        const drop = st.tab === 'gate' ? 5 : st.tab === 'market' ? 9 : 7;
        const corrY = by + drop;
        if (ex > cx + 4) {
          const turnX = Math.max(cx + 6, gutterX);
          d = Math.abs(ey - corrY) <= 2
            ? `M${cx} ${by}V${corrY}H${ex}`
            : `M${cx} ${by}V${corrY}H${turnX}V${ey}H${ex}`;
          dx = cx; dy = by;
        }
      } else {
        const rightStart = Math.max(sBox.right, fullSelBox.right);
        const sx = Math.round(rightStart - bBox.left);
        const sy = Math.round(midY - bBox.top);
        if (ex > sx + 2) {
          const turnX = Math.max(sx + 4, Math.min(ex - 3, gutterX));
          d = Math.abs(ey - sy) <= 3 ? `M${sx} ${sy}H${ex}` : `M${sx} ${sy}H${turnX}V${ey}H${ex}`;
          dx = sx; dy = sy;
        }
      }
    }
    p.setAttribute('d', d);
    if (d && drawLine === true && motionOn() && typeof p.animate === 'function') {
      if (p._anim) p._anim.cancel();
      p._anim = p.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], {
        duration: Math.max(90, Math.round(240 * motionScale())),
        easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
      });
    }
    if (dot) {
      if (d) { dot.setAttribute('cx', dx); dot.setAttribute('cy', dy); dot.removeAttribute('hidden'); dot.style.display = ''; }
      else { dot.setAttribute('hidden', ''); dot.style.display = 'none'; }
    }
  }

  function staggerEvLines(zrIn) {
    const targets = [];
    const h2 = $('#ev-t', zrIn);
    if (h2) targets.push(h2);
    const b = $('#ev-b', zrIn);
    if (b && b.children.length) targets.push(b);
    const body = $('#ev-body', zrIn);
    if (body) {
      for (const child of Array.from(body.children)) {
        if (child.classList.contains('ev-sec')) {
          for (const sub of Array.from(child.children)) targets.push(sub);
        } else {
          targets.push(child);
        }
      }
    }
    targets.slice(0, 10).forEach((el, idx) => {
      el.style.setProperty('--ld', `${Math.round(Math.min(idx, 5) * 30 * motionScale())}ms`);
      el.classList.add('ev-line-in');
    });
  }

  let evAnimToken = 0;
  function cancelEvAnims(zr, zrIn, body) {
    if (zr && zr._evAnim) { zr._evAnim.cancel(); zr._evAnim = null; }
    if (zrIn && zrIn._evAnim) { zrIn._evAnim.cancel(); zrIn._evAnim = null; }
    if (body && body._evAnim) { body._evAnim.cancel(); body._evAnim = null; }
    if (zr) zr._closingEv = false;
  }

  function setEvPicked(spec, animate) {
    const zr = $('#z-right'), unsel = $('#ev-unselected'), zrIn = $('#zr-in');
    const k = $('#ev-k'), t = $('#ev-t'), b = $('#ev-b'), body = $('#ev-body');
    const backBtn = $('#ev-back-btn');
    const board = $('#board');
    if (!zr || !zrIn || !k || !body) return;
    evAnimToken++;
    const wasPicked = zr.classList.contains('is-picked') && !zrIn.hidden && !zr._closingEv;
    cancelEvAnims(zr, zrIn, body);
    const isBand = !!(board && board.dataset.layout === 'band' && mode() !== 'sheet');
    const beforeZrTop = (!wasPicked && isBand && animate && motionOn()) ? zr.getBoundingClientRect().top : null;
    zr.classList.remove('has-default-panel');
    zr.classList.add('is-picked');
    if (unsel) unsel.hidden = true;
    zrIn.hidden = false;
    if (backBtn) {
      if (spec.backLabel) {
        backBtn.textContent = spec.backLabel;
        backBtn.hidden = false;
      } else {
        backBtn.hidden = true;
      }
    }
    k.textContent = spec.kicker || cp('evKickerPick');
    t.textContent = spec.title || '';
    b.innerHTML = (spec.badges || []).join('');
    body.innerHTML = typeof spec.body === 'string' ? spec.body : '';
    if (spec.body && typeof spec.body !== 'string') body.appendChild(spec.body);
    body.scrollTop = 0;
    if (spec.after) { try { spec.after(body); } catch (e) { console.error(e); } }
    if (animate && motionOn()) {
      const dist = isBand ? Math.max(zr.offsetHeight || 0, Math.abs((beforeZrTop != null ? beforeZrTop - zr.getBoundingClientRect().top : 0))) : 0;
      const { dur, easing } = panelTiming(true, dist);
      if (!wasPicked && dur > 0 && typeof zrIn.animate === 'function') {
        if (isBand) {
          const rawDy = beforeZrTop != null ? (beforeZrTop - zr.getBoundingClientRect().top) : 0;
          const dy = Math.abs(rawDy) >= 1 ? Math.max(-110, Math.min(110, rawDy)) : 14;
          zr._evAnim = zr.animate([
            { transform: `translate3d(0,${dy.toFixed(2)}px,0)` },
            { transform: 'translate3d(0,0,0)' },
          ], { duration: dur, easing });
          zrIn._evAnim = zrIn.animate([
            { transform: 'scaleY(0)', opacity: 0 },
            { transform: 'scaleY(1)', opacity: 1 },
          ], { duration: dur, easing });
        } else {
          zrIn._evAnim = zrIn.animate([
            { opacity: 0, transform: 'translate3d(16px,0,0)' },
            { opacity: 1, transform: 'translate3d(0,0,0)' },
          ], { duration: dur, easing });
        }
        body._evAnim = body.animate([
          { opacity: 0, offset: 0 },
          { opacity: 0, offset: 0.42 },
          { opacity: 1, offset: 1 },
        ], { duration: dur, easing });
      } else {
        staggerEvLines(zrIn);
      }
    }
    requestAnimationFrame(() => { syncRightScrollCue(); updateSelLink(animate === true); });
  }

  function unselectedConclusion(c) {
    const curC = c || ctx();
    const tb = tabs[st.tab];
    if (tb && typeof tb.conclusion === 'function') {
      try {
        const custom = tb.conclusion(curC);
        if (custom) return custom;
      } catch (e) { console.error(e); }
    }
    const base = curC.base || S['기준별'][st.base];
    if (st.tab === 'graph') {
      const spec = tb && tb.defaultEv ? tb.defaultEv(curC) : null;
      const tmp = document.createElement('div');
      tmp.innerHTML = (spec && spec.body) || '';
      return { text: firstSentence(tmp.textContent), flag: '' };
    }
    const bk = TAB_BRIEF_KEY[st.tab];
    if (base && bk) {
      const row = lineOf(base, bk);
      if (row) {
        return {
          text: firstSentence(row['문장']),
          flag: row['원문대조'] ? (row['원문대조글'] || cp('flagDefault')) : '',
        };
      }
    }
    const fb = base && base['범위'] ? firstSentence(base['범위']['문장']) : '';
    return { text: fb, flag: '' };
  }

  function populateUnselectedEv(zr, unsel, curC) {
    const tb = tabs[st.tab];
    if (tb && typeof tb.renderDefaultRight === 'function') {
      zr.classList.add('has-default-panel');
      unsel.classList.add('is-custom-panel');
      tb.renderDefaultRight(unsel, curC);
      return;
    }
    zr.classList.remove('has-default-panel');
    unsel.classList.remove('is-custom-panel');
    const info = unselectedConclusion(curC);
    const scopeBadge = (curC.peerScope !== 'all' && st.tab !== 'graph' && !(info && info.scoped)) ? ' ' + fullScopeTag() : '';
    unsel.innerHTML = info && info.text ? `<p class="read-concl">${esc(info.text)}${scopeBadge}</p>` : '';
  }

  function showUnselectedEv(c, animateClose) {
    const zr = $('#z-right'), unsel = $('#ev-unselected'), zrIn = $('#zr-in'), body = $('#ev-body');
    const board = $('#board');
    if (!zr || !unsel) return;
    const curC = c || ctx();
    clearSelLink();
    const wasPicked = zr.classList.contains('is-picked') && zrIn && !zrIn.hidden && !zr._closingEv;
    const isBandNow = !!(board && board.dataset.layout === 'band' && mode() !== 'sheet');
    const { dur, easing } = panelTiming(false, isBandNow ? (zr.offsetHeight || 0) : 0);
    if (wasPicked && animateClose && dur > 0 && mode() !== 'sheet' && typeof zrIn.animate === 'function') {
      const token = ++evAnimToken;
      cancelEvAnims(zr, zrIn, body);
      zr._closingEv = true;
      const isBand = !!(board && board.dataset.layout === 'band');
      populateUnselectedEv(zr, unsel, curC);
      if (isBand) {
        const curTop = zr.getBoundingClientRect().top;
        zr.classList.remove('is-picked');
        zrIn.hidden = true;
        unsel.hidden = false;
        const targetTop = zr.getBoundingClientRect().top;
        unsel.hidden = true;
        zrIn.hidden = false;
        zr.classList.add('is-picked');
        const rawDy = targetTop - curTop;
        const dy = Math.abs(rawDy) >= 1 ? Math.max(-110, Math.min(110, rawDy)) : 14;
        zr._evAnim = zr.animate([
          { transform: 'translate3d(0,0,0)' },
          { transform: `translate3d(0,${dy.toFixed(2)}px,0)` },
        ], { duration: dur, easing });
        zrIn._evAnim = zrIn.animate([
          { transform: 'scaleY(1)', opacity: 1 },
          { transform: 'scaleY(0)', opacity: 0 },
        ], { duration: dur, easing });
      } else {
        zrIn._evAnim = zrIn.animate([
          { opacity: 1, transform: 'translate3d(0,0,0)' },
          { opacity: 0, transform: 'translate3d(16px,0,0)' },
        ], { duration: dur, easing });
      }
      zrIn._evAnim.onfinish = () => {
        if (token !== evAnimToken) return;
        cancelEvAnims(zr, zrIn, body);
        zr.classList.remove('is-picked');
        zrIn.hidden = true;
        unsel.hidden = false;
        populateUnselectedEv(zr, unsel, ctx());
        if (typeof unsel.animate === 'function' && motionOn()) {
          unsel.animate([{ opacity: 0 }, { opacity: 1 }], { duration: Math.min(200, dur), easing });
        }
      };
      return;
    }
    evAnimToken++;
    cancelEvAnims(zr, zrIn, body);
    zr.classList.remove('is-picked');
    if (zrIn) zrIn.hidden = true;
    unsel.hidden = false;
    populateUnselectedEv(zr, unsel, curC);
  }

  function showEv(spec, o = {}) {
    setEvPicked(spec, o.animate !== false);
    if (o.open !== false && mode() === 'sheet') openEv();
  }
  function openEv() {
    if (mode() !== 'sheet') return;
    if (!EV.open) { EV.open = true; document.body.classList.add('ev-open'); }
    sheetPad();
  }
  function hideEv() {
    if (!EV.open) return;
    const zr = $('#z-right');
    const { dur, easing } = panelTiming(false);
    if (mode() === 'sheet' && dur > 0 && zr && typeof zr.animate === 'function') {
      const token = ++evAnimToken;
      const anim = zr.animate([
        { transform: 'translate3d(0,0,0)', opacity: 1 },
        { transform: 'translate3d(0,28px,0)', opacity: 0 },
      ], { duration: dur, easing });
      anim.onfinish = () => {
        if (token !== evAnimToken) return;
        EV.open = false;
        document.body.classList.remove('ev-open');
        sheetPad();
      };
      return;
    }
    EV.open = false; document.body.classList.remove('ev-open');
    sheetPad();
  }
  function sheetPad() {
    const zr = $('#z-right');
    const h = EV.open && mode() === 'sheet' && zr ? zr.offsetHeight : 0;
    document.documentElement.style.setProperty('--sheet-h', h + 'px');
  }

  function legendHTML() {
    return `<dl class="legend">
      <dt>${verdict('better')}</dt><dd>${esc(cp('lgBetter'))}</dd>
      <dt>${verdict('only')}</dt><dd>${esc(cp('lgOnly'))}</dd>
      <dt>${verdict('worse')}</dt><dd>${esc(cp('lgWorse'))}</dd>
      <dt>${verdict('same')}</dt><dd>${esc(cp('lgSame'))}</dd>
      <dt>${verdict('diff')}</dt><dd>${esc(cp('lgDiff'))}</dd>
      <dt>${verdict('none')}</dt><dd>${esc(cp('lgNone'))}</dd>
      <dt>${verdict('unknown')}</dt><dd>${esc(cp('lgUnknown'))}</dd>
      <dt>${flagText(cp('flagShort'))}</dt><dd>${esc(cp('lgFlag'))}</dd>
      <dt>${scope('all')}</dt><dd>${esc(cp('lgScopeAll'))}</dd>
      <dt>${scope('base')}</dt><dd>${esc(cp('lgScopeBase'))}</dd>
      <dt>${scope('now')}</dt><dd>${esc(cp('lgScopeNow'))}</dd>
    </dl>`;
  }
  registerLegend('verdict', 'legendVerdictTitle', legendHTML);

  function syncRovingTabindex() {
    const zlItems = $$('#z-left .zl-item');
    if (zlItems.length) {
      let onIdx = zlItems.findIndex(b => b.classList.contains('is-on') || b.getAttribute('aria-selected') === 'true');
      if (onIdx < 0) onIdx = 0;
      zlItems.forEach((b, k) => { b.tabIndex = k === onIdx ? 0 : -1; });
    }
    const gridItems = $$('#z-center [data-grid-r][data-grid-c]');
    if (gridItems.length) {
      let selIdx = gridItems.findIndex(b => b.classList.contains('is-sel'));
      if (selIdx < 0) selIdx = 0;
      gridItems.forEach((b, k) => { b.tabIndex = k === selIdx ? 0 : -1; });
    }
    const insRows = $$('#view-insight .lrow[data-pick]');
    if (insRows.length) {
      let selIdx = insRows.findIndex(li => li.classList.contains('is-sel'));
      if (selIdx < 0) selIdx = 0;
      insRows.forEach((li, k) => {
        const hit = $('.lrow-hit', li);
        if (hit) hit.tabIndex = k === selIdx ? 0 : -1;
        $$('input[data-act="ins-pick"]', li).forEach(ck => { ck.tabIndex = -1; });
      });
    }
  }

  function remark(id) {
    const v = viewOf(id) || $('#z-center');
    const board = $('#board');
    const key = st.sel[id];
    if (board) board.classList.toggle('has-sel', id !== 'brief' && key != null);
    if (!v) return;
    for (const el of $$('[data-pick]', v)) {
      const on = key != null && el.dataset.pick === String(key);
      el.classList.toggle('is-sel', on);
      const hit = el.matches('button') ? el : $('.lrow-hit', el);
      if (hit) hit.setAttribute('aria-pressed', String(on));
    }
    syncRovingTabindex();
  }

  function fitSel() {
    updateSelLink();
  }

  function applySelectionState(animate, c) {
    const id = st.tab;
    if (id === 'brief') return;
    const curC = c || ctx();
    remark(id);
    const key = st.sel[id];
    const t = tabs[id];
    if (key != null && t && t.pick) {
      let spec = null;
      try { spec = t.pick(String(key), curC); } catch (e) { console.error(e); }
      if (spec) {
        setEvPicked(spec, animate);
      } else {
        delete st.sel[id];
        remark(id);
        hideSelGlide();
        showUnselectedEv(curC, false);
        hideEv();
      }
    } else {
      hideSelGlide();
      showUnselectedEv(curC, animate === true);
      hideEv();
    }
    syncHeaderAndPath(curC);
  }

  function select(key, o = {}) {
    if (st.tab === 'brief') return;
    if (key == null) return unselect(o);
    const same = st.sel[st.tab] === String(key);
    if (same && o.toggleOff) return unselect(o);
    const prevBox = (!same && o.animate !== false) ? measureSelBox(st.tab) : null;
    st.sel[st.tab] = String(key);
    if (o.push !== false && booted && !same) pushHistory(new Set(['pick']));
    const curC = ctx();
    applySelectionState(o.animate !== false, curC);
    const nextBox = (!same && o.animate !== false && prevBox) ? measureSelBox(st.tab) : null;
    if (prevBox && nextBox) playSelGlide(prevBox, nextBox);
    if (st.sel[st.tab] != null && mode() === 'sheet' && o.open !== false) openEv();
    const root = viewOf(st.tab) || $('#z-center');
    const el = root && $(`[data-pick="${CSS.escape(String(key))}"]`, root);
    if (el && o.focus) {
      const hit = el.matches('button,tr,[tabindex]') ? el : ($('.lrow-hit', el) || el);
      try { hit.focus({ preventScroll: true }); } catch (e) { /* */ }
    }
    if (curAimEl && el) refreshAimReticle();
    if (el && o.reveal !== false && mode() === 'sheet') setTimeout(() => reveal(el), 240);
    placeGuides();
    requestAnimationFrame(() => updateSelLink(o.animate !== false && !same));
    emit('select', st.tab, String(key));
  }

  function unselect(o = {}) {
    const prevKey = st.sel[st.tab];
    const had = prevKey != null;
    delete st.sel[st.tab];
    delete st.sub[st.tab];
    hideSelGlide();
    if (o.push !== false && booted && had) pushHistory(new Set(['pick']));
    const curC = ctx();
    applySelectionState(o.animate !== false && had, curC);
    hideEv();
    if (o.restoreFocus !== false && prevKey != null) {
      const root = viewOf(st.tab) || $('#z-center');
      const el = root && $(`[data-pick="${CSS.escape(String(prevKey))}"]`, root);
      if (el) {
        const hit = el.matches('button,tr,[tabindex]') ? el : ($('.lrow-hit', el) || el);
        try { hit.focus({ preventScroll: true }); } catch (e) { /* */ }
      }
    }
    placeGuides();
    emit('select', st.tab, null);
  }

  function setGroup(grpVal, o = {}) {
    const id = st.tab;
    if (id === 'brief') return;
    const next = grpVal == null ? '' : String(grpVal);
    if ((st.grp[id] || '') === next) {
      if (o.toggleOff && next !== '') st.grp[id] = '';
      else return;
    } else {
      st.grp[id] = next;
    }
    if (o.clearSel !== false) delete st.sel[id];
    if (o.push !== false && booted) pushHistory(new Set(['grp']));
    renderActiveScreen(ctx(), 'grp');
    if (o.focusKey != null) {
      const btnEl = $(`#z-left [data-zl="${CSS.escape(String(o.focusKey))}"]`);
      if (btnEl) { try { btnEl.focus({ preventScroll: true }); } catch (e) { /* */ } }
    }
  }

  function returnToHome(fromTab) {
    const prev = fromTab && fromTab !== 'brief' ? fromTab : 'market';
    set({ tab: 'brief' });
    const target = $('#tab-' + prev) || $(`#home-panel [data-rtab="${prev}"]`);
    if (target) { try { target.focus({ preventScroll: true }); } catch (e) { /* */ } }
  }

  // ---------- 눌러서 여는 전체 표 및 문장 창(#data-modal) ----------
  let modalTrigger = null;
  let modalRefreshFn = null;
  let modalAnimToken = 0;
  function cancelModalAnims(m) {
    const sc = m && $('.dm-scrim', m);
    const bx = m && $('.dm-box', m);
    if (sc && sc._dmAnim) { sc._dmAnim.cancel(); sc._dmAnim = null; }
    if (bx && bx._dmAnim) { bx._dmAnim.cancel(); bx._dmAnim = null; }
    if (m) m._closing = false;
  }
  function openModal(spec) {
    const m = $('#data-modal');
    if (!m || !spec) return;
    closeHelp(false, true);
    modalAnimToken++;
    cancelModalAnims(m);
    modalTrigger = spec.trigger || document.activeElement || null;
    modalRefreshFn = typeof spec.render === 'function' ? spec.render : null;
    const content = modalRefreshFn ? modalRefreshFn(ctx()) : spec;
    fillModal(content);
    m.hidden = false;
    const { dur, easing } = panelTiming(true);
    if (dur > 0) {
      const sc = $('.dm-scrim', m);
      const bx = $('.dm-box', m);
      if (sc && typeof sc.animate === 'function') {
        sc._dmAnim = sc.animate([{ opacity: 0 }, { opacity: 1 }], { duration: dur, easing });
      }
      if (bx && typeof bx.animate === 'function') {
        bx._dmAnim = bx.animate([
          { opacity: 0, transform: 'translate3d(0,16px,0)' },
          { opacity: 1, transform: 'translate3d(0,0,0)' },
        ], { duration: dur, easing });
      }
    }
    const closeBtn = $('#dm-x', m);
    if (closeBtn) { try { closeBtn.focus({ preventScroll: true }); } catch (e) { /* */ } }
  }
  function fillModal(content) {
    const m = $('#data-modal');
    if (!m || !content) return;
    $('#dm-k', m).textContent = content.kicker || '';
    $('#dm-title', m).textContent = content.title || '';
    $('#dm-b', m).innerHTML = (content.badges || []).join('');
    $('#dm-acts', m).innerHTML = content.actions || '';
    const body = $('#dm-body', m);
    body.innerHTML = typeof content.html === 'string' ? content.html : '';
    if (content.html && typeof content.html !== 'string') body.appendChild(content.html);
    if (typeof content.after === 'function') {
      try { content.after(body, ctx()); } catch (e) { console.error(e); }
    }
  }
  function refreshModalIfOpen() {
    const m = $('#data-modal');
    if (!m || m.hidden || m._closing || !modalRefreshFn) return;
    fillModal(modalRefreshFn(ctx()));
  }
  function closeModal(restoreFocus, immediate) {
    const m = $('#data-modal');
    if (!m || m.hidden) return false;
    if (m._closing && !immediate) return true;
    modalRefreshFn = null;
    const prev = modalTrigger;
    modalTrigger = null;
    if (restoreFocus && prev && document.contains(prev)) {
      try { prev.focus({ preventScroll: true }); } catch (e) { /* */ }
    }
    const { dur, easing } = panelTiming(false);
    const bx = $('.dm-box', m);
    const sc = $('.dm-scrim', m);
    if (!immediate && dur > 0 && bx && typeof bx.animate === 'function') {
      const token = ++modalAnimToken;
      cancelModalAnims(m);
      m._closing = true;
      if (sc && typeof sc.animate === 'function') {
        sc._dmAnim = sc.animate([{ opacity: 1 }, { opacity: 0 }], { duration: dur, easing });
      }
      bx._dmAnim = bx.animate([
        { opacity: 1, transform: 'translate3d(0,0,0)' },
        { opacity: 0, transform: 'translate3d(0,16px,0)' },
      ], { duration: dur, easing });
      bx._dmAnim.onfinish = () => {
        if (token !== modalAnimToken) return;
        cancelModalAnims(m);
        m.hidden = true;
        $('#dm-body', m).innerHTML = '';
      };
      return true;
    }
    modalAnimToken++;
    cancelModalAnims(m);
    m.hidden = true;
    $('#dm-body', m).innerHTML = '';
    return true;
  }

  function closeActMenu() {
    const wrap = $('#th-act-wrap'), btnEl = $('#act-menu-btn'), box = $('#th-act-btns');
    if (!wrap || !wrap.classList.contains('is-open')) return false;
    if (btnEl) btnEl.setAttribute('aria-expanded', 'false');
    const { dur, easing } = panelTiming(false);
    if (dur > 0 && box && typeof box.animate === 'function') {
      const anim = box.animate([{ opacity: 1, transform: 'translate3d(0,0,0)' }, { opacity: 0, transform: 'translate3d(0,-8px,0)' }], { duration: dur, easing });
      anim.onfinish = () => wrap.classList.remove('is-open');
      return true;
    }
    wrap.classList.remove('is-open');
    return true;
  }

  function stepUp() {
    if (closeActMenu()) { const mb = $('#act-menu-btn'); if (mb) mb.focus(); return true; }
    if (closeHelp(true)) return true;
    if (closeModal(true)) return true;
    if (condOpen) { setCondOpen(false); const b = $('#cond-sum'); if (b) b.focus(); return true; }
    if (scopeOpen) { setScopeOpen(false); const b = $('#scope-tgl'); if (b) b.focus(); return true; }
    if (EV.open && mode() === 'sheet') { unselect({ restoreFocus: true }); return true; }
    if (st.sel[st.tab] != null) { unselect({ restoreFocus: true }); return true; }
    const curGrp = st.grp[st.tab];
    if (st.tab !== 'brief' && curGrp) {
      setGroup('', { focusKey: '' });
      const firstZl = $('#z-left .zl-item');
      if (firstZl) { try { firstZl.focus({ preventScroll: true }); } catch (e) { /* */ } }
      return true;
    }
    if (st.tab !== 'brief') {
      returnToHome(st.tab);
      return true;
    }
    return false;
  }

  function showTab(id, opts = {}) {
    closeModal(false, true);
    renderActiveScreen(ctx(new Set(['tab'])), 'tab');
    if (opts.scroll !== false && booted && innerWidth < 1280) scrollTo({ top: 0, behavior: 'auto' });
    emit('tab', id);
  }

  function notify(changed, opts = {}) {
    syncCond();
    renderScope();
    for (const id of SCREEN_IDS) {
      if (id !== st.tab && tabs[id]) tabs[id]._dirty = true;
    }
    renderActiveScreen(ctx(changed), 'change');
    refreshModalIfOpen();
    emit('change', ctx(changed), opts);
  }

  function scrollInZone(target, behavior) {
    if (!target) return;
    const sm = behavior || (motionOn() ? 'smooth' : 'auto');
    const sc = target.closest && target.closest('#dm-body, #ev-body, #z-center, #z-left, #home-panel');
    if (sc && (innerWidth >= 1280 || sc.scrollHeight > sc.clientHeight + 2)) {
      const scRect = sc.getBoundingClientRect();
      const tRect = target.getBoundingClientRect();
      const maxTop = Math.max(0, sc.scrollHeight - sc.clientHeight);
      const nextTop = Math.max(0, Math.min(maxTop, sc.scrollTop + (tRect.top - scRect.top) - 6));
      sc.scrollTo({ top: nextTop, behavior: sm });
      return;
    }
    const top = Math.max(0, window.scrollY + target.getBoundingClientRect().top - 40);
    window.scrollTo({ top, behavior: sm });
  }

  function reveal(el) {
    if (!el) return;
    const sm = motionOn() ? 'smooth' : 'auto';
    const sc = el.closest && el.closest('#dm-body, #ev-body, #z-center, #z-left, #home-panel');
    if (sc && (innerWidth >= 1280 || sc.scrollHeight > sc.clientHeight + 2)) {
      const scRect = sc.getBoundingClientRect();
      const r = el.getBoundingClientRect();
      const pad = 12;
      if (r.top < scRect.top + pad) {
        sc.scrollBy({ top: r.top - scRect.top - pad, behavior: sm });
      } else if (r.bottom > scRect.bottom - pad) {
        sc.scrollBy({ top: Math.min(r.bottom - scRect.bottom + pad, r.top - scRect.top - pad), behavior: sm });
      }
      return;
    }
    const r = el.getBoundingClientRect();
    const top = 36;
    const bottom = innerHeight - (EV.open && mode() === 'sheet' ? $('#z-right').offsetHeight : 0) - 12;
    if (r.top < top) scrollBy({ top: r.top - top, behavior: sm });
    else if (r.bottom > bottom) scrollBy({ top: Math.min(r.bottom - bottom, r.top - top), behavior: sm });
  }
  function go(tabId, o = {}) {
    if (!TAB_IDS.includes(tabId)) tabId = TAB_BY_NAME[tabId] || tabId;
    if (!TAB_IDS.includes(tabId)) return;
    closeModal(false, true);
    if (o.grp != null) st.grp[tabId] = o.grp;
    set({ tab: tabId });
    const nextBtn = $('#tab-' + tabId);
    if (nextBtn && !o.focus) { try { nextBtn.focus({ preventScroll: true }); } catch (e) { /* */ } }
    const t = tabs[tabId];
    if (o.focus != null && t && t.focus) {
      setTimeout(() => {
        try {
          const sec = viewOf(tabId);
          t.focus(o.focus, sec ? $('.vbody', sec) : $('#z-center'), ctx());
        } catch (e) { console.error(e); }
      }, 30);
    }
  }

  // ---------- 복사와 인쇄 ----------
  function scopeLine() {
    const base = S['기준별'][st.base];
    const pSet = new Set(activePeerOrgs());
    const vids = base ? (st.peerScope === 'all' ? base['맞붙는종형'] : base['맞붙는종형'].filter(v => pSet.has((vinfo(v) || {})['기관코드']))) : [];
    const peers = vids.length ? vids.map(vname).join(', ') : cp('condPeerNone');
    return cp('scopeLineTpl', { base: vname(st.base), peers, seg: condSegOnly(), asof: asofText(), notice: S['고지'] });
  }
  const clean = s => String(s == null ? '' : s).replace(/[\t\r\n]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
  function copyText(text, msg) {
    const done = () => toast(msg || cp('copyOk'));
    const fallback = () => {
      const ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0';
      document.body.appendChild(ta); ta.select();
      let ok = false; try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      ta.remove();
      toast(ok ? (msg || cp('copyOk')) : cp('copyFail'));
    };
    try {
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback);
      else fallback();
    } catch (e) { fallback(); }
  }
  function copyRows(head, rows, o = {}) {
    const lines = [];
    if (o.scope !== false) lines.push(o.title ? `${clean(o.title)} / ${scopeLine()}` : scopeLine());
    if (head && head.length) lines.push(head.map(clean).join('\t'));
    for (const r of rows) lines.push(r.map(clean).join('\t'));
    copyText(lines.join('\r\n'), cp('copyRowsOkTpl', { n: rows.length }));
  }
  function copyTable(tbl, o = {}) {
    if (typeof tbl === 'string') tbl = document.getElementById(tbl);
    if (!tbl) return;
    const gcp = td => (td.dataset.copy != null ? td.dataset.copy : td.dataset.cp != null ? td.dataset.cp : td.textContent);
    const head = $$('thead th', tbl).map(gcp);
    const rows = $$('tbody tr', tbl).filter(tr => !tr.classList.contains('no-copy')).map(tr => $$('td,th', tr).map(gcp));
    const cap = $('caption', tbl);
    copyRows(head, rows, { title: o.title || (cap ? cap.textContent : ''), scope: o.scope });
  }
  function copyCurrentSummary() {
    const t = tabs[st.tab];
    if (t && typeof t.copySummary === 'function') {
      t.copySummary(ctx());
      return;
    }
    const base = S['기준별'][st.base];
    if (!base) return;
    const NAMES = { '가': cp('briefRowGa'), '나': cp('briefRowNa'), '다': cp('briefRowDa'), '라': cp('briefRowRa'), '마': cp('briefRowMa') };
    const rows = (base['브리핑'] || []).map(b => [b['줄'], NAMES[b['줄']] || '', b['범위'], b['문장'], b['갈곳']]);
    copyRows(cp('briefCopyCols').split(','), rows, { title: cp('briefCopyTitle') });
  }
  function print(el, o = {}) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (!el) return;
    const root = $('#print-root');
    root.innerHTML = `<div class="ph">${esc(S['고지'])}${o.card ? `<span class="mk">${esc(cp('printMark'))}</span>` : ''}<span class="sc">${esc(o.title ? o.title + ' / ' : '')}${esc(scopeLine())}</span></div>`;
    root.appendChild(el.cloneNode(true));
    document.body.classList.add('printing');
    const done = () => { document.body.classList.remove('printing'); root.innerHTML = ''; window.removeEventListener('afterprint', done); };
    window.addEventListener('afterprint', done);
    try { window.print(); } catch (e) { done(); }
    setTimeout(() => { if (document.body.classList.contains('printing') && !matchMedia('print').matches) done(); }, 1500);
  }
  let toastT = 0;
  function toast(msg) {
    const t = $('#toast'); t.textContent = msg; t.classList.add('on');
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('on'), 2600);
  }

  // ---------- 안내선 ----------
  function placeGuides() {
    const g = $('#guides'); if (!g) return;
    const W = innerWidth, H = innerHeight;
    const anchorEl = st.tab === 'brief' ? $('#home-panel') : $('#rtabs');
    if (!anchorEl) return;
    const rtBox = anchorEl.getBoundingClientRect();
    const topY = Math.round(rtBox.top);
    const botY = H - 72;
    const centers = [Math.round(rtBox.left), Math.round(rtBox.right)];
    let staticBox = $('.gl-static', g);
    let redTk = $('.tk.red', g);
    if (!staticBox) {
      g.innerHTML = '<div class="gl-static"></div><i class="tk red" hidden></i>';
      staticBox = $('.gl-static', g);
      redTk = $('.tk.red', g);
    }
    const sig = `${W}|${H}|${topY}|${botY}|${centers.join(',')}`;
    if (staticBox._sig !== sig) {
      staticBox._sig = sig;
      let html = `<i class="hl" style="top:${topY}px"></i><i class="hl" style="top:${botY}px"></i>`;
      for (const c of centers) {
        if (c < 0 || c > W) continue;
        html += `<i class="gl c" style="left:${c}px"></i>`;
        html += `<i class="tk" style="left:${c}px;top:${topY}px"></i><i class="tk" style="left:${c}px;top:${botY}px"></i>`;
      }
      staticBox.innerHTML = html;
    }
    const activeTab = st.tab !== 'brief' ? $('#rtabs #tab-' + st.tab) : null;
    if (redTk) {
      if (activeTab) {
        const ab = activeTab.getBoundingClientRect();
        const tx = Math.round(ab.left + 14);
        const wasHidden = redTk.hidden;
        if (wasHidden) redTk.style.transition = 'none';
        redTk.style.top = topY + 'px';
        redTk.style.setProperty('--tx', tx + 'px');
        redTk.hidden = false;
        if (wasHidden) { void redTk.offsetWidth; redTk.style.transition = ''; }
      } else {
        redTk.hidden = true;
      }
    }
  }

  function applySkin() {
    document.documentElement.dataset.theme = st.skin;
    const b = $('#skin');
    if (b) {
      const tx = st.skin === 'dark' ? cp('skinLight') : cp('skinDark');
      b.innerHTML = `${IC.moon}<span class="tgl-tx">${esc(tx)}</span>`;
      b.setAttribute('aria-label', tx);
      b.title = tx;
      b.setAttribute('aria-pressed', String(st.skin === 'dark'));
    }
    store.set(LS_SKIN, st.skin);
  }
  function applyMotion() {
    document.documentElement.dataset.motion = st.motion;
    applyBgParallax(st.tab);
    const b = $('#motion');
    if (b) {
      const label = st.motion === 'on' ? cp('motionOn') : st.motion === 'calm' ? cp('motionCalm') : cp('motionOff');
      const full = `${cp('motionWord')} ${label}`;
      b.innerHTML = `${IC.wave}<span class="tgl-tx">${esc(cp('motionWord'))} <b>${esc(label)}</b></span>`;
      b.setAttribute('aria-label', full);
      b.title = full;
      b.dataset.motionMode = st.motion;
      b.setAttribute('aria-pressed', String(st.motion !== 'off'));
    }
    store.set(LS_MOTION, st.motion);
  }
  const asofText = () => String(S['자료시각'] || '').replace('T', ' ').slice(0, 16);

  // ---------- 물음표 풀이, 범례, 비교 범위 팝오버, 말풍선 ----------
  let helpAnchor = null;
  let helpAnimToken = 0;
  function cancelHelpAnim(pop) {
    if (pop && pop._popAnim) { pop._popAnim.cancel(); pop._popAnim = null; }
    if (pop) pop._closing = false;
  }
  function openHelpPop(pop, btnEl) {
    helpAnimToken++;
    cancelHelpAnim(pop);
    pop.hidden = false;
    positionPop(pop, btnEl);
    const { dur, easing } = panelTiming(true);
    if (dur > 0 && typeof pop.animate === 'function') {
      pop._popAnim = pop.animate([
        { opacity: 0, transform: 'translate3d(0,-10px,0)' },
        { opacity: 1, transform: 'translate3d(0,0,0)' },
      ], { duration: dur, easing });
    }
  }
  function closeHelp(restoreFocus, immediate) {
    const pop = $('#help-pop');
    if (!pop || pop.hidden) return false;
    if (pop._closing && !immediate) return false;
    const prev = helpAnchor;
    helpAnchor = null;
    if (prev) {
      prev.setAttribute('aria-expanded', 'false');
      if (restoreFocus) { try { prev.focus(); } catch (e) { /* */ } }
    }
    const { dur, easing } = panelTiming(false);
    if (!immediate && dur > 0 && typeof pop.animate === 'function') {
      const token = ++helpAnimToken;
      cancelHelpAnim(pop);
      pop._closing = true;
      pop._popAnim = pop.animate([
        { opacity: 1, transform: 'translate3d(0,0,0)' },
        { opacity: 0, transform: 'translate3d(0,-10px,0)' },
      ], { duration: dur, easing });
      pop._popAnim.onfinish = () => {
        if (token !== helpAnimToken) return;
        cancelHelpAnim(pop);
        pop.hidden = true;
        pop.classList.remove('is-leg', 'is-peer');
        pop.innerHTML = '';
      };
      return true;
    }
    helpAnimToken++;
    cancelHelpAnim(pop);
    pop.hidden = true;
    pop.classList.remove('is-leg', 'is-peer');
    pop.innerHTML = '';
    return true;
  }
  function positionPop(pop, anchor) {
    const r = anchor.getBoundingClientRect();
    const pw = pop.offsetWidth || 380, ph = pop.offsetHeight || 180;
    const left = Math.max(8, Math.min(innerWidth - pw - 8, Math.round(r.left)));
    const below = r.bottom + 8 + ph <= innerHeight - 8;
    const top = below ? Math.round(r.bottom + 8) : Math.max(8, Math.round(r.top - ph - 8));
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';
  }
  function toggleHelp(btnEl) {
    const item = TERMS[btnEl.dataset.help];
    if (!item) return;
    const pop = $('#help-pop');
    if (helpAnchor === btnEl && !pop.hidden && !pop._closing) { closeHelp(false); return; }
    closeHelp(false, true);
    helpAnchor = btnEl;
    btnEl.setAttribute('aria-expanded', 'true');
    pop.classList.remove('is-leg', 'is-peer');
    const fontSrc = $('#font-notice-src');
    const fontTxt = (btnEl.dataset.help === 'scope-band' && fontSrc) ? fontSrc.textContent.trim() : '';
    const fontSec = fontTxt ? `<div class="help-sec"><strong class="help-sub">${esc(cp('footFontHead'))}</strong><p class="help-font">${esc(fontTxt)}</p></div>` : '';
    pop.innerHTML = `<div class="help-h"><span>${esc(cp(item.titleKey))}</span><button type="button" class="help-x" data-help-close="1" aria-label="${esc(cp('legendCloseAria'))}"><svg width="11" height="11" viewBox="0 0 14 14" aria-hidden="true"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8"/></svg></button></div><div class="help-sec"><p class="help-p">${esc(cp(item.bodyKey))}</p></div>${fontSec}`;
    openHelpPop(pop, btnEl);
  }
  function toggleLegend(btnEl) {
    const key = btnEl.dataset.legend || st.tab || 'verdict';
    const spec = LEGENDS[key] || LEGENDS.verdict;
    if (!spec) return;
    const pop = $('#help-pop');
    if (helpAnchor === btnEl && !pop.hidden && !pop._closing) { closeHelp(false); return; }
    closeHelp(false, true);
    helpAnchor = btnEl;
    btnEl.setAttribute('aria-expanded', 'true');
    pop.classList.remove('is-peer');
    pop.classList.add('is-leg');
    pop.innerHTML = `<div class="help-h"><span>${esc(cp(spec.titleKey))}</span><button type="button" class="help-x" data-help-close="1" aria-label="${esc(cp('legendCloseAria'))}"><svg width="11" height="11" viewBox="0 0 14 14" aria-hidden="true"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8"/></svg></button></div>${spec.htmlFn(ctx())}`;
    openHelpPop(pop, btnEl);
  }
  function renderPeerPopBody() {
    const modes = [
      { v: 'all', t: cp('peerAll') },
      { v: 'life', t: cp('peerLife') },
      { v: 'nonlife', t: cp('peerNonLife') },
      { v: 'custom', t: cp('peerCustom') },
    ];
    const picked = new Set(st.peerPick || []);
    const groups = [
      { k: 'life', t: cp('peerLifeGroup'), list: PEER_ORGS.filter(o => orgSector(o) === 'life') },
      { k: 'nonlife', t: cp('peerNonLifeGroup'), list: PEER_ORGS.filter(o => orgSector(o) === 'nonlife') },
    ].filter(g => g.list.length > 0);
    return `<div class="help-h"><span>${esc(cp('peerTitle'))}</span><button type="button" class="help-x" data-help-close="1" aria-label="${esc(cp('legendCloseAria'))}"><svg width="11" height="11" viewBox="0 0 14 14" aria-hidden="true"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8"/></svg></button></div>
      <div class="peer-modes" role="radiogroup" aria-label="${esc(cp('peerTitle'))}">
        ${modes.map(m => `<button type="button" class="peer-m${st.peerScope === m.v ? ' is-on' : ''}" role="radio" aria-checked="${st.peerScope === m.v}" data-peer-mode="${m.v}">${esc(m.t)}</button>`).join('')}
      </div>
      <div class="peer-orgs${st.peerScope === 'custom' ? ' is-custom' : ''}">
        ${groups.map(g => `<div class="peer-grp"><div class="peer-gh">${esc(g.t)} (${g.list.length})</div><div class="peer-gl">${g.list.map(code => {
          const on = st.peerScope === 'custom' ? picked.has(code) : activePeerOrgs().includes(code);
          return `<button type="button" class="peer-chk${on ? ' is-on' : ''}" data-peer-org="${esc(code)}" aria-pressed="${on}"><i></i><span>${esc(orgShort(code))}</span></button>`;
        }).join('')}</div></div>`).join('')}
      </div>`;
  }
  function togglePeerPop(btnEl) {
    const pop = $('#help-pop');
    if (helpAnchor === btnEl && !pop.hidden && !pop._closing) { closeHelp(false); return; }
    closeHelp(false, true);
    helpAnchor = btnEl;
    btnEl.setAttribute('aria-expanded', 'true');
    pop.classList.remove('is-leg');
    pop.classList.add('is-peer');
    pop.innerHTML = renderPeerPopBody();
    openHelpPop(pop, btnEl);
  }

  // ---------- 이름표(#hud-tip), 조준 표식(#aim-reticle), 문지르기([data-scrub-row]) ----------
  let tipAnchor = null, curAimEl = null, scrollMuteUntil = 0, suppressClickUntil = 0;
  let touchScrub = null;

  function buildTipHTML(el) {
    if (!el || !el.dataset) return '';
    const ttl = el.dataset.tipTitle;
    const sub = el.dataset.tipSub;
    const chip = el.dataset.tipChip;
    const chipsJson = el.dataset.tipChips;
    const badge = el.dataset.tipBadge;
    if (ttl || sub || chip || chipsJson || badge) {
      const chips = [];
      if (chipsJson) {
        try {
          for (const [k, label] of JSON.parse(chipsJson)) chips.push(verdict(k, label));
        } catch (e) { /* */ }
      } else if (chip) {
        chips.push(verdict(chip));
      }
      if (badge) chips.push(tag(badge));
      return `${ttl ? `<span class="ht-t">${esc(ttl)}</span>` : ''}${sub ? `<span class="ht-s">${esc(sub)}</span>` : ''}${chips.length ? `<span class="ht-b">${chips.join('')}</span>` : ''}`;
    }
    const text = el.dataset.tip;
    return text ? esc(text) : '';
  }

  function measureBoxRect(el) {
    if (!el || !el.isConnected) return null;
    const boxEl = el.querySelector('[data-aim-box]') || el;
    return boxEl.getBoundingClientRect();
  }

  function showHudTip(el, preRect) {
    const tip = $('#hud-tip');
    if (!tip || !el || !el.isConnected) return;
    if (el === tipAnchor && !tip.hidden) return;
    const html = buildTipHTML(el);
    if (!html) { hideHudTip(); return; }
    const r = preRect || measureBoxRect(el);
    const minTop = 30;
    if (!r || r.width < 1 || r.bottom <= minTop || r.top >= innerHeight) { hideHudTip(); return; }
    tipAnchor = el;
    const halfClamp = Math.min(180, Math.floor(innerWidth * 0.42));
    const cx = Math.max(halfClamp, Math.min(innerWidth - halfClamp, Math.round(r.left + r.width / 2)));
    const above = r.top >= 96;
    const ty = above ? Math.round(r.top - 10) : Math.min(innerHeight - 36, Math.max(minTop, Math.round(r.bottom + 10)));
    tip.style.setProperty('--tip-x', cx + 'px');
    tip.style.setProperty('--tip-y', ty + 'px');
    tip.style.setProperty('--tip-vy', above ? '-100%' : '0%');
    tip.innerHTML = html;
    tip.hidden = false;
  }

  function hideHudTip() {
    tipAnchor = null;
    const tip = $('#hud-tip');
    if (tip) tip.hidden = true;
  }

  function refreshAimReticle(preRect) {
    if (!curAimEl || !curAimEl.isConnected) { hideAimReticle(); return; }
    const ret = $('#aim-reticle');
    if (!ret) return;
    if (curAimEl.dataset.nodata === '1' || curAimEl.getAttribute('aria-disabled') === 'true') {
      ret.hidden = true;
      return;
    }
    const r = preRect || measureBoxRect(curAimEl);
    if (!r || r.width < 2 || r.height < 2 || r.bottom < 24 || r.top > innerHeight) {
      ret.hidden = true;
      return;
    }
    const wasHidden = ret.hidden;
    ret.dataset.shape = curAimEl.dataset.aim === 'circle' ? 'circle' : 'rect';
    ret.classList.toggle('is-sel-aim', curAimEl.classList.contains('is-sel'));
    ret.style.setProperty('--ar-w', Math.round(r.width) + 'px');
    ret.style.setProperty('--ar-h', Math.round(r.height) + 'px');
    if (wasHidden) {
      ret.style.transition = 'none';
      ret.classList.remove('is-tight', 'is-press');
    }
    ret.style.setProperty('--ar-x', Math.round(r.left) + 'px');
    ret.style.setProperty('--ar-y', Math.round(r.top) + 'px');
    ret.hidden = false;
    if (wasHidden) {
      requestAnimationFrame(() => {
        ret.style.transition = '';
        if (!ret.hidden) ret.classList.add('is-tight');
      });
    } else {
      ret.classList.add('is-tight');
    }
  }

  function setAimTarget(el, preRect) {
    if (el === curAimEl) return;
    const r = el ? (preRect || measureBoxRect(el)) : null;
    const prev = curAimEl;
    if (prev) prev.classList.remove('is-aim');
    curAimEl = el || null;
    if (curAimEl) {
      curAimEl.classList.add('is-aim');
      refreshAimReticle(r);
    } else {
      const ret = $('#aim-reticle');
      if (ret) { ret.hidden = true; ret.classList.remove('is-tight', 'is-press'); }
    }
    emit('aim', curAimEl, prev);
  }

  function hideAimReticle() {
    if (curAimEl) setAimTarget(null);
    else {
      const ret = $('#aim-reticle');
      if (ret) { ret.hidden = true; ret.classList.remove('is-tight', 'is-press'); }
    }
  }

  function findScrubCandidate(rowEl, clientX) {
    const key = innerWidth + '|' + Math.round(window.scrollY || 0) + '|' + rowEl.childElementCount;
    let zones = rowEl._scrubKey === key ? rowEl._scrubZones : null;
    if (!zones) {
      zones = [];
      $$('[data-aim],[data-pick]', rowEl).forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width >= 1 && r.height >= 1) zones.push({ el, left: r.left, right: r.right });
      });
      rowEl._scrubKey = key;
      rowEl._scrubZones = zones;
    }
    if (!zones.length) return null;
    let best = null, bestDist = Infinity;
    for (let i = 0; i < zones.length; i++) {
      const z = zones[i];
      if (clientX >= z.left && clientX <= z.right) return z.el;
      const dist = clientX < z.left ? (z.left - clientX) : (clientX - z.right);
      if (dist < bestDist) { bestDist = dist; best = z.el; }
    }
    return bestDist <= 42 ? best : null;
  }

  document.addEventListener('pointerover', e => {
    if (e.pointerType === 'touch' || performance.now() < scrollMuteUntil) return;
    const aimEl = e.target.closest && e.target.closest('[data-aim]');
    const tipEl = (e.target.closest && e.target.closest('[data-tip],[data-tip-title]'))
      || (aimEl && (aimEl.dataset.tip || aimEl.dataset.tipTitle) ? aimEl : null);
    // 쓰기 전에 필요한 좌표를 한꺼번에 읽어 강제 동기 레이아웃을 0으로 만든다
    const aimChanged = aimEl && aimEl !== curAimEl;
    const tipChanged = tipEl && (tipEl !== tipAnchor || ($('#hud-tip') && $('#hud-tip').hidden));
    const aimRect = aimChanged ? measureBoxRect(aimEl) : null;
    const tipRect = tipChanged ? (tipEl === aimEl && aimRect ? aimRect : measureBoxRect(tipEl)) : null;

    if (aimEl) setAimTarget(aimEl, aimRect);
    else if (curAimEl && !e.target.closest('[data-scrub-row]')) hideAimReticle();
    if (tipEl) showHudTip(tipEl, tipRect);
    else if (tipAnchor && !e.target.closest('[data-scrub-row]')) hideHudTip();
  });

  document.addEventListener('pointermove', e => {
    if (performance.now() < scrollMuteUntil) return;
    if (e.pointerType === 'touch') {
      if (!touchScrub || touchScrub.id !== e.pointerId) return;
      const dx = e.clientX - touchScrub.x0, dy = e.clientY - touchScrub.y0;
      if (!touchScrub.active) {
        if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) { touchScrub = null; return; }
        if (Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(dy)) touchScrub.active = true;
      }
      if (touchScrub && touchScrub.active) {
        const cand = findScrubCandidate(touchScrub.row, e.clientX);
        if (cand && cand !== curAimEl) {
          const r = measureBoxRect(cand);
          setAimTarget(cand, r);
          showHudTip(cand, r);
        }
      }
      return;
    }
    const scrubRow = e.target.closest && e.target.closest('[data-scrub-row]');
    if (scrubRow) {
      const direct = e.target.closest && e.target.closest('[data-aim],[data-pick]');
      const cand = direct || findScrubCandidate(scrubRow, e.clientX);
      if (cand && (cand !== curAimEl || cand !== tipAnchor)) {
        const r = measureBoxRect(cand);
        if (cand.dataset.aim) setAimTarget(cand, r);
        if (cand.dataset.tip || cand.dataset.tipTitle) showHudTip(cand, r);
      }
    }
  }, { passive: true });

  document.addEventListener('pointerout', e => {
    if (e.pointerType === 'touch') return;
    const rel = e.relatedTarget;
    if (curAimEl && (!rel || (!curAimEl.contains(rel) && !(rel.closest && rel.closest('[data-scrub-row]'))))) {
      const nextAim = rel && rel.closest && rel.closest('[data-aim]');
      if (!nextAim) hideAimReticle();
    }
    if (tipAnchor && (!rel || (!tipAnchor.contains(rel) && !(rel.closest && rel.closest('[data-scrub-row]'))))) {
      const nextTip = rel && rel.closest && rel.closest('[data-tip],[data-tip-title]');
      if (!nextTip) hideHudTip();
    }
  });

  document.addEventListener('pointerdown', e => {
    if (e.pointerType === 'touch') {
      const scrubRow = e.target.closest && e.target.closest('[data-scrub-row]');
      if (scrubRow) {
        touchScrub = { id: e.pointerId, row: scrubRow, x0: e.clientX, y0: e.clientY, active: false };
      } else {
        touchScrub = null;
      }
      return;
    }
    const ret = $('#aim-reticle');
    if (ret && !ret.hidden && curAimEl && curAimEl.dataset.nodata !== '1') ret.classList.add('is-press');
  }, { passive: true });

  function finishPointerPress(e) {
    const ret = $('#aim-reticle');
    if (ret) ret.classList.remove('is-press');
    if (e && e.pointerType === 'touch' && touchScrub && touchScrub.id === e.pointerId) {
      const wasActive = touchScrub.active;
      const picked = curAimEl;
      touchScrub = null;
      if (wasActive) {
        suppressClickUntil = performance.now() + 380;
        hideAimReticle();
        hideHudTip();
        if (picked && picked.dataset.pick && picked.dataset.nodata !== '1') {
          select(picked.dataset.pick, { focus: true });
        }
      }
    }
  }
  document.addEventListener('pointerup', finishPointerPress, { passive: true });
  document.addEventListener('pointercancel', finishPointerPress, { passive: true });

  document.addEventListener('focusin', e => {
    if (e.target.matches && !e.target.matches(':focus-visible')) return;
    const aimEl = e.target.closest && e.target.closest('[data-aim]');
    if (aimEl) setAimTarget(aimEl);
    const el = e.target.closest && e.target.closest('[data-tip],[data-tip-title]');
    if (el) showHudTip(el);
  });
  document.addEventListener('focusout', () => { hideAimReticle(); hideHudTip(); });

  addEventListener('scroll', () => { scrollMuteUntil = performance.now() + 220; closeHelp(false); hideAimReticle(); hideHudTip(); }, { passive: true });
  on('tab', () => { closeHelp(false); hideAimReticle(); hideHudTip(); });
  on('change', (_, opts) => { if (!opts || !opts.keepPop) closeHelp(false); hideAimReticle(); hideHudTip(); });

  // ---------- 위임 클릭과 키보드 ----------
  document.addEventListener('click', e => {
    if (performance.now() < suppressClickUntil) { e.stopPropagation(); e.preventDefault(); return; }
    hideHudTip();
    const mc = e.target.closest('[data-modal-close]');
    if (mc) { e.stopPropagation(); closeModal(true); return; }
    const hc = e.target.closest('[data-help-close]');
    if (hc) { e.stopPropagation(); closeHelp(true); return; }
    const pb = e.target.closest('[data-peer-pop]');
    if (pb) { e.stopPropagation(); togglePeerPop(pb); return; }
    const pm = e.target.closest('[data-peer-mode]');
    if (pm) {
      e.stopPropagation();
      const modeVal = pm.dataset.peerMode;
      const patch = { peerScope: modeVal };
      if (modeVal === 'custom' && (!st.peerPick || !st.peerPick.length)) patch.peerPick = PEER_ORGS.slice();
      set(patch, { keepPop: true });
      const pop = $('#help-pop');
      if (pop && !pop.hidden) { pop.innerHTML = renderPeerPopBody(); positionPop(pop, helpAnchor || pb || $('#peer-tgl')); }
      return;
    }
    const po = e.target.closest('[data-peer-org]');
    if (po) {
      e.stopPropagation();
      const code = po.dataset.peerOrg;
      const basePick = st.peerScope === 'custom' ? (st.peerPick || []).slice() : activePeerOrgs();
      const next = basePick.includes(code) ? basePick.filter(x => x !== code) : basePick.concat([code]);
      set({ peerScope: 'custom', peerPick: PEER_ORGS.filter(o => next.includes(o)) }, { keepPop: true });
      const pop = $('#help-pop');
      if (pop && !pop.hidden) pop.innerHTML = renderPeerPopBody();
      return;
    }
    const am = e.target.closest('#act-menu-btn');
    if (am) {
      e.stopPropagation();
      const wrap = $('#th-act-wrap'), box = $('#th-act-btns');
      if (wrap) {
        const opening = !wrap.classList.contains('is-open');
        if (opening) {
          wrap.classList.add('is-open');
          am.setAttribute('aria-expanded', 'true');
          const { dur, easing } = panelTiming(true);
          if (dur > 0 && box && typeof box.animate === 'function') {
            box.animate([{ opacity: 0, transform: 'translate3d(0,-8px,0)' }, { opacity: 1, transform: 'translate3d(0,0,0)' }], { duration: dur, easing });
          }
        } else {
          closeActMenu();
        }
      }
      return;
    }
    if (!e.target.closest('#th-act-wrap')) closeActMenu();
    else if (e.target.closest('#th-act-btns button')) setTimeout(closeActMenu, 0);

    const detSum = e.target.closest('details.zr-det > summary');
    if (detSum && motionOn()) {
      const det = detSum.parentElement;
      const bodyEl = det && $('.zr-det-b', det);
      if (det && bodyEl && typeof bodyEl.animate === 'function') {
        e.preventDefault();
        if (det._detAnim) { det._detAnim.cancel(); det._detAnim = null; }
        if (!det.open) {
          det.open = true;
          det.dispatchEvent(new Event('toggle'));
          const { dur, easing } = panelTiming(true, bodyEl.offsetHeight || 160);
          if (dur > 0) {
            det._detAnim = bodyEl.animate([
              { opacity: 0, transform: 'scaleY(0)' },
              { opacity: 1, transform: 'scaleY(1)' },
            ], { duration: dur, easing });
          }
        } else {
          const { dur, easing } = panelTiming(false, bodyEl.offsetHeight || 160);
          if (dur > 0) {
            det._detAnim = bodyEl.animate([
              { opacity: 1, transform: 'scaleY(1)' },
              { opacity: 0, transform: 'scaleY(0)' },
            ], { duration: dur, easing });
            det._detAnim.onfinish = () => {
              det._detAnim = null;
              det.open = false;
              det.dispatchEvent(new Event('toggle'));
            };
          } else {
            det.open = false;
            det.dispatchEvent(new Event('toggle'));
          }
        }
        return;
      }
    }

    const hb = e.target.closest('[data-help]');
    if (hb) { e.stopPropagation(); toggleHelp(hb); return; }
    const lb = e.target.closest('[data-legend]');
    if (lb) { e.stopPropagation(); toggleLegend(lb); return; }
    if (!e.target.closest('#help-pop')) closeHelp(false);

    const rt = e.target.closest('[data-rtab]');
    if (rt) {
      e.stopPropagation();
      const id = rt.dataset.rtab;
      if (id === 'brief' || st.tab === id) {
        returnToHome(st.tab === 'brief' ? id : st.tab);
        return;
      }
      set({ tab: id });
      const nextBtn = $('#tab-' + st.tab) || $('#tab-' + id);
      if (nextBtn) { try { nextBtn.focus({ preventScroll: true }); } catch (ex) { /* */ } }
      return;
    }

    const pi = e.target.closest('[data-path-idx]');
    if (pi) {
      e.stopPropagation();
      const idx = +pi.dataset.pathIdx;
      if (idx === 0) {
        returnToHome(st.tab);
      } else if (idx === 1) {
        if (st.sel[st.tab] != null) unselect({ restoreFocus: true });
        else if (st.grp[st.tab]) setGroup('', { focusKey: '' });
      }
      return;
    }

    const lu = e.target.closest('[data-layer-up]');
    if (lu) { e.stopPropagation(); stepUp(); return; }

    const zl = e.target.closest('[data-zl]');
    if (zl) {
      e.stopPropagation();
      setGroup(zl.dataset.zl, { toggleOff: zl.dataset.zlToggle === '1', focusKey: zl.dataset.zl });
      return;
    }

    const js = e.target.closest('[data-jump-sec]');
    if (js) {
      e.stopPropagation();
      $$('#z-left [data-jump-sec]').forEach(x => {
        const on = x === js;
        x.classList.toggle('is-on', on);
        x.setAttribute('aria-selected', String(on));
      });
      syncRovingTabindex();
      const target = document.getElementById(js.dataset.jumpSec);
      if (target) scrollInZone(target);
      return;
    }

    const a = e.target.closest('[data-act],[data-go],button[data-copy],button[data-print]');
    if (a) {
      if (a.dataset.go) { e.stopPropagation(); go(a.dataset.go, { focus: a.dataset.focus, grp: a.dataset.grp }); return; }
      if (a.dataset.copy) { e.stopPropagation(); copyTable(a.dataset.copy, { title: a.dataset.title }); return; }
      if (a.dataset.print) { e.stopPropagation(); print(a.dataset.print, { title: a.dataset.title, card: a.dataset.card === '1' }); return; }
      if (a.dataset.act === 'base-to') { set({ base: a.dataset.v }); return; }
      if (a.dataset.act === 'copy-summary') { e.stopPropagation(); copyCurrentSummary(); return; }
      if (a.dataset.act) return;
    }

    const mp = e.target.closest('#dm-body [data-pick]');
    if (mp && !e.target.closest('.live')) {
      const pickKey = mp.dataset.pick;
      closeModal(false, true);
      select(pickKey, { focus: true });
      return;
    }

    const p = e.target.closest('#z-center [data-pick]');
    if (p && !e.target.closest('.live')) {
      if (p.dataset.nodata === '1') { showHudTip(p); return; }
      select(p.dataset.pick, { focus: true, toggleOff: p.dataset.toggle === '1' });
      return;
    }
    const sr = e.target.closest('#z-center [data-scrub-row]');
    if (sr && !e.target.closest('button,a,input,select,.live')) {
      const cand = findScrubCandidate(sr, e.clientX);
      if (cand && cand.dataset.pick) {
        if (cand.dataset.nodata === '1') { showHudTip(cand); return; }
        select(cand.dataset.pick, { focus: true, toggleOff: cand.dataset.toggle === '1' });
      }
    }
  });

  document.addEventListener('keydown', e => {
    // 1. 고리 탭 줄 및 첫 화면 다섯 묶음 좌우 화살표 이동
    const inRtab = e.target.closest && e.target.closest('[data-rtab]');
    if (inRtab && ['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(e.key)) {
      const scopeRoot = st.tab === 'brief' ? $('#home-panel') : $('#rtabs');
      const items = scopeRoot ? $$('[data-rtab]', scopeRoot) : [];
      if (!items.length) return;
      const i = items.indexOf(inRtab);
      if (i < 0) return;
      let j = i;
      if (e.key === 'ArrowRight') j = (i + 1) % items.length;
      if (e.key === 'ArrowLeft') j = (i + items.length - 1) % items.length;
      if (e.key === 'Home') j = 0;
      if (e.key === 'End') j = items.length - 1;
      e.preventDefault();
      if (st.tab === 'brief' || items[j].dataset.rtab === 'brief') {
        items.forEach((b, k) => { b.tabIndex = k === j ? 0 : -1; });
        items[j].focus();
      } else {
        set({ tab: items[j].dataset.rtab });
        const nb = $('#tab-' + items[j].dataset.rtab);
        if (nb) nb.focus();
      }
      return;
    }

    // 2. 왼쪽 분류 구역 상하 화살표 이동
    const inZl = e.target.closest && e.target.closest('#z-left .zl-item');
    if (inZl && (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Home' || e.key === 'End')) {
      const items = $$('#z-left .zl-item');
      const i = items.indexOf(inZl);
      let j = i;
      if (e.key === 'ArrowDown') j = Math.min(items.length - 1, i + 1);
      if (e.key === 'ArrowUp') j = Math.max(0, i - 1);
      if (e.key === 'Home') j = 0;
      if (e.key === 'End') j = items.length - 1;
      if (j !== i) {
        e.preventDefault();
        items.forEach((b, k) => { b.tabIndex = k === j ? 0 : -1; });
        items[j].focus();
      }
      return;
    }

    // 3. 무대 단위 도형 격자 화살표 이동([data-grid-r][data-grid-c])
    const cellBtn = e.target.closest && e.target.closest('#z-center [data-grid-r][data-grid-c]');
    if (cellBtn && ['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp'].includes(e.key)) {
      const r = +cellBtn.dataset.gridR, c = +cellBtn.dataset.gridC;
      const nr = e.key === 'ArrowDown' ? r + 1 : e.key === 'ArrowUp' ? r - 1 : r;
      const nc = e.key === 'ArrowRight' ? c + 1 : e.key === 'ArrowLeft' ? c - 1 : c;
      const next = $(`#z-center [data-grid-r="${nr}"][data-grid-c="${nc}"]`);
      if (next) {
        e.preventDefault();
        $$('#z-center [data-grid-r][data-grid-c]').forEach(b => { b.tabIndex = b === next ? 0 : -1; });
        next.focus();
      }
      return;
    }

    const trPick = e.target.closest && e.target.closest('tr[data-pick]');
    if (trPick && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      if (trPick.closest('#dm-body')) {
        const pk = trPick.dataset.pick;
        closeModal(false, true);
        select(pk, { focus: true });
      } else {
        select(trPick.dataset.pick, { focus: true });
      }
      return;
    }

    if (e.key === 'Escape') {
      if (stepUp()) { e.preventDefault(); return; }
    }
    const typing = e.target.closest && e.target.closest('input,select,textarea');
    if (typing) return;
    if (e.key === ']' || e.key === '[') {
      const curIdx = SCREEN_IDS.indexOf(st.tab);
      const nextIdx = curIdx < 0 ? 0 : (curIdx + (e.key === ']' ? 1 : SCREEN_IDS.length - 1)) % SCREEN_IDS.length;
      set({ tab: SCREEN_IDS[nextIdx] });
    }
  });

  // ---------- 탭 등록 ----------
  function registerTab(def) {
    if (!def || !TAB_IDS.includes(def.id)) throw new Error('Unknown tab: ' + (def && def.id));
    tabs[def.id] = Object.assign({ kicker: '' }, def, { _dirty: true, _drawn: false });
    if (booted && def.id === st.tab) renderActiveScreen(ctx(), 'register');
  }

  // ---------- 시작 ----------
  function boot() {
    const saved = { skin: store.get(LS_SKIN), motion: store.get(LS_MOTION) };
    if (saved.skin === 'dark' || saved.skin === 'light') st.skin = saved.skin;
    if (saved.motion === 'on' || saved.motion === 'calm' || saved.motion === 'off') st.motion = saved.motion;
    else if (matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) st.motion = 'calm';
    else st.motion = 'on';
    const initHash = decodeHash(location.hash);
    Object.assign(st, initHash.patch);
    lastRenderedTab = st.tab;
    activeRenderedTab = st.tab;
    if (initHash.grp != null) st.grp[st.tab] = initHash.grp;
    if (initHash.pick != null) st.sel[st.tab] = initHash.pick;
    if (st.since == null) st.surg = false;
    applySkin(); applyMotion();

    if ($('#boot-loader')) $('#boot-loader').setAttribute('aria-label', cp('bootAria'));
    if ($('#rtabs')) $('#rtabs').setAttribute('aria-label', cp('tabsAria'));
    if ($('#lpath')) $('#lpath').setAttribute('aria-label', cp('pathAria'));
    if ($('#z-left')) $('#z-left').setAttribute('aria-label', cp('zoneLeftAria'));
    if ($('#z-center')) $('#z-center').setAttribute('aria-label', cp('zoneCenterAria'));
    if ($('#z-right')) $('#z-right').setAttribute('aria-label', cp('evAria'));
    if ($('#ev-pnm-t')) $('#ev-pnm-t').textContent = cp('evPanelName');
    if ($('#ev-x')) $('#ev-x').setAttribute('aria-label', cp('evCloseAria'));
    if ($('#dm-x')) $('#dm-x').setAttribute('aria-label', cp('legendCloseAria'));
    if ($('#dm-x-t')) $('#dm-x-t').textContent = cp('modalCloseBtn');
    if ($('#zr-more')) $('#zr-more').innerHTML = `<span>${esc(cp('evMoreBtn'))}</span> ${IC.chevD}`;
    if ($('#foot-notice-h')) $('#foot-notice-h').textContent = cp('footNoticeHead');
    if ($('#foot-disclaimer')) $('#foot-disclaimer').textContent = cp('footDisclaimer');
    if ($('#asof-label')) $('#asof-label').textContent = cp('footAsof');
    if ($('#foot-font-h')) $('#foot-font-h').textContent = cp('footFontHead');
    $('#asof').textContent = asofText();
    $('#notice-t').textContent = S['고지'];
    $('#foot-notice').textContent = S['고지'];
    const eh = $('#ev-help');
    if (eh) eh.outerHTML = help('ev-panel', cp('evPanelName'));

    renderCond();
    renderScope();
    ensureLegacySections();

    $('#skin').addEventListener('click', () => set({ skin: st.skin === 'dark' ? 'light' : 'dark' }));
    $('#motion').addEventListener('click', () => {
      const next = st.motion === 'on' ? 'calm' : st.motion === 'calm' ? 'off' : 'on';
      set({ motion: next });
    });
    $('#ev-x').addEventListener('click', () => unselect({ restoreFocus: true }));
    const evBackBtn = $('#ev-back-btn');
    if (evBackBtn) evBackBtn.addEventListener('click', () => unselect({ restoreFocus: true }));
    const rtabsEl = $('#rtabs'), rtCueL = $('#rt-cue-l'), rtCueR = $('#rt-cue-r');
    if (rtabsEl) {
      rtabsEl.addEventListener('scroll', () => { syncRtabsCue(false); placeGuides(); }, { passive: true });
    }
    if (rtCueL && rtabsEl) rtCueL.addEventListener('click', () => rtabsEl.scrollBy({ left: -160, behavior: motionOn() ? 'smooth' : 'auto' }));
    if (rtCueR && rtabsEl) rtCueR.addEventListener('click', () => rtabsEl.scrollBy({ left: 160, behavior: motionOn() ? 'smooth' : 'auto' }));
    const zc = $('#z-center');
    if (zc) zc.addEventListener('scroll', () => { hideAimReticle(); requestAnimationFrame(() => updateSelLink(false)); }, { passive: true });
    const evBody = $('#ev-body'), zrMore = $('#zr-more');
    if (evBody) {
      evBody.addEventListener('scroll', syncRightScrollCue, { passive: true });
      evBody.addEventListener('toggle', () => setTimeout(syncRightScrollCue, 20), true);
    }
    if (zrMore && evBody) {
      zrMore.addEventListener('click', () => evBody.scrollBy({ top: 180, behavior: motionOn() ? 'smooth' : 'auto' }));
    }

    let rz = 0, lastMode = mode();
    addEventListener('resize', () => {
      syncRtabsCue(false);
      clearTimeout(rz);
      rz = setTimeout(() => {
        const m = mode();
        if (m !== lastMode) {
          if (m !== 'sheet') hideEv();
          lastMode = m;
          if (st.tab !== 'brief' && st.sel[st.tab] != null) applySelectionState(false);
        }
        closeHelp(false); hideAimReticle(); hideHudTip();
        syncRtabsCue(true); sheetPad(); placeGuides(); updateSelLink(false); syncRightScrollCue(); emit('resize', m);
      }, 80);
    });

    booted = true;
    try { history.replaceState({ c4: 1 }, '', encodeHash()); } catch (e) { /* */ }
    renderActiveScreen(ctx(), 'tab');
    setTimeout(() => { placeGuides(); updateSelLink(false); syncRightScrollCue(); }, 50);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { placeGuides(); updateSelLink(false); });
  }

  window.App = {
    S, D: DD, COPY, t: cp, SCREEN_IDS, TAB_IDS, TAB_NAME, TAB_BY_NAME, ORG_ORDER, PEER_ORGS, REF,
    get state() { return { ...st, peerPick: st.peerPick.slice(), grp: { ...st.grp }, sel: { ...st.sel }, sub: { ...st.sub } }; },
    set, setGroup, on, ctx: () => ctx(), registerTab, go, select, unselect, stepUp, returnToHome, reveal, scrollInZone, panelTiming,
    openModal, closeModal, updateSelLink, flipElement, countUp,
    aim: { set: setAimTarget, hide: hideAimReticle, showTip: showHudTip, hideTip: hideHudTip },
    ev: { show: showEv, open: openEv, close: () => unselect(), def: () => showUnselectedEv(), legend: legendHTML },
    ui: UI, txt: TXT, mode, motionOn, motionRich, motionScale,
    cellOf, cellCounts, gateFlowRows, coverStageStacks, scopedPairs, firstSentence,
    segPatch, segPatchText, samePatch, activePeerOrgs, activeOrgs, orgSector, inScope, filterScopeCodes, ringTabMetrics,
    limitOf, mapOf, condSummary, condSegOnly, scopeLine, asofText,
    copyText, copyRows, copyTable, print, toast, fitSel,
    boot,
  };
})();
