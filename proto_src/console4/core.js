/* 시안 4 공통 실행부. 문구 표, 상태, 0~3층 탐색(조건 접기, 경로, Esc, 뒤로 가기), 범례와 말풍선, 근거 기둥, 복사와 인쇄.
   규약은 API.md 와 요청 22에 있다. 화면 코드가 쓰는 문구는 아래 COPY 한 곳에서 읽는다. */
(function () {
  'use strict';

  const S = window.__BOOT_S || JSON.parse(document.getElementById('sales-data').textContent);
  try { delete window.__BOOT_S; } catch (e) { /* */ }
  const DD = (typeof D !== 'undefined') ? D : null;

  // ---------- 화면 문구 표(한 곳에서 관리, 나중에 실무 용어로 일괄 교체 가능) ----------
  const COPY = {
    appTitle: '영업 분석 콘솔',
    bootAria: '화면 열기 진행률',
    tabsAria: '분석 단계',
    skinDark: '짙은 화면',
    skinLight: '밝은 화면',
    motionWord: '움직임',
    motionOn: '켬',
    motionOff: '끔',
    condAria: '조건 줄',
    condOpenBtn: '조건 바꾸기',
    condCloseBtn: '조건 접기',
    condBasePrefix: '기준',
    condPeerPrefix: '상대',
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
    condPeersHint: '기준 종형에 맞춰 정해집니다',
    condRenewal: '갱신 유형',
    condRenewalHint: '고객군 지도에만 씁니다',
    condRenAll: '전체',
    condRenRenew: '갱신',
    condRenNon: '비갱신',
    condMiniTitle: '조건 줄로 올라가기',

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
    evAria: '근거 기둥',
    evKickerDefault: '요약',
    evKickerPick: '근거',
    evPanelName: '관계와 근거 패널',
    evCloseAria: '근거 닫기',
    footNoticeHead: '고지.',
    footDisclaimer: '상품요약서와 사업방법서 같은 공시 문서에서 뽑은 값으로 계산했고, 판매 시책, 수수료, 손해율, 인수 판정은 다루지 않습니다.',
    footAsof: '자료 기준',
    footFontHead: '글꼴.',

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

    legendBtn: '범례',
    legendCloseAria: '창 닫기',
    helpSuffixAria: ' 뜻 보기',
    legendVerdictTitle: '판정과 범위 범례',
    lgBetter: '같은 담보를 견줘 우체국 조건이 나은 것',
    lgOnly: '견준 상대에는 없고 우체국에만 있는 담보',
    lgWorse: '같은 담보를 견줘 우체국 조건이 못한 것',
    lgSame: '조건이 같은 것',
    lgDiff: '지급 형태나 판매 구성이 달라 우열을 매기지 않은 것',
    lgNone: '상대에는 있고 우체국에는 없는 담보',
    lgUnknown: '검토 대기라 아직 견주지 않은 것',
    lgFlag: '화면에 옮긴 값이 사업방법서 원문과 같은지 사람이 확인해야 합니다',
    lgSel: '지금 고른 항목. 그 항목의 근거가 오른쪽 기둥에 뜹니다',
    lgScopeAll: '기준 종형과 조건을 바꿔도 그대로인 값입니다.',
    lgScopeBase: '기준 종형을 바꾸면 다시 계산하는 값입니다.',
    lgScopeNow: '조건 줄의 나이, 성별, 이력을 따라 바뀌는 값입니다.',

    termScopeTitle: '범위 띠',
    termScopeBody: '위쪽 줄은 지금 고른 기준 종형과 맞붙는 상대 상품, 공통 담보 쌍의 수를 보여 줍니다. 아래쪽 줄은 조건 줄의 나이, 성별, 이력이 고객군 지도에서 어느 관문 칸에 해당하는지 보여 줍니다.',
    termEvTitle: '관계와 근거 패널',
    termEvBody: '본문에서 도형이나 칸을 고르면 그 항목의 문장, 관계 식, 원문 문서 쪽 번호를 이 영역에 보여 줍니다. 아무것도 고르지 않았을 때는 지금 탭의 결론 한 문장만 보여 줍니다.',
    termBaseTitle: '기준 종형과 선택 종형',
    termBaseBody: '기준 종형은 조건 줄에서 고른 우체국 상품 종형이며, 비교 상대는 그 종형의 심사 유형과 갱신 구조에 맞춰 정해집니다. 선택 종형 배지가 붙은 숫자와 문장은 이 기준 종형을 바꿀 때 함께 다시 계산하는 값입니다.',
    termJourneyTitle: '치료 여정 격자',
    termJourneyBody: '암, 뇌혈관, 심장 같은 보장 대분류와 진단, 수술, 치료, 입원, 통원의 다섯 단계가 만나는 칸마다 회사별 표준담보 수를 견준 표입니다. 빈 단계나 담보 수 차이를 한눈에 살피는 용도이며, 조건의 우열은 담보 비교표에서 따집니다.',
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
    tabMissing: '이 탭의 파일이 아직 없습니다.',
    tabErrorPrefix: '이 탭을 그리다 멈췄습니다: ',
    chevPrevSuffix: ' 앞 값',
    chevNextSuffix: ' 다음 값',
    tabPrevAria: '앞 분석 단계',
    tabNextAria: '다음 분석 단계',
    stepDecSuffix: ' 하나 줄이기',
    stepIncSuffix: ' 하나 늘리기',

    // 탭 1(브리핑) 전용 문구
    briefKicker: '분석 요약',
    briefRowGa: '고객군 지형',
    briefRowNa: '개정과 시장',
    briefRowDa: '가입 관문과 한도',
    briefRowRa: '담보 포지션',
    briefRowMa: '영업 인사이트',
    briefConclTpl: '기준 {kind}: 고객군 {open}/{cells}칸 열림, 개정 변동 {rev}개, 관문 차이 {gate}곳, 공통 담보 {cmp}/{pairs}쌍 견줌, 인사이트 {ins}건입니다.',
    briefEvConclKicker: '결론 요약',
    briefModeText: '문장으로 보기',
    briefModeShape: '도형으로 보기',
    briefCopyBtn: '요약 복사',
    briefCopyTitle: '브리핑 분석 요약',
    briefCopyCols: '줄,구역,범위,문장,갈 곳',
    briefLegendTitle: '브리핑 도형 범례',
    briefLgMedalGold: '금색 이중 고리와 호: 우체국 단독 열림이나 신설, 보유 강점 몫',
    briefLgMedalRed: '빨강 원과 네 귀 사선: 지금 고른 메달 하나',
    briefLgMedalTick: '방사형 잔눈금: 전체 가운데 채우지 못한 몫이나 검토 대기',
    briefLgMapOpen: '진한 금색 면(우리만 열림)과 밝은 면(함께 열림): 우체국 간편 열림',
    briefLgMapOurs: '회색 면(점선 네모 기호): 우리 간편 닫힘, 일반심사 확인',
    briefLgMapGo: '안쪽 점선 테두리: 상대가 관문만 수집한 종형으로 열리는 칸',
    briefLgMapNow: '검은 이중 테두리: 지금 조건에 해당하는 고객군 칸',
    briefLgStepGold: '금색 타일: 우체국 담보가 있는 치료 단계, 빗금은 없는 단계',
    briefGoTabTpl: '{tab} 탭으로',
    briefGoDetailTpl: '{tab} 탭에서 자세히',
    briefUpBtn: '뒤로',
    briefL2GaTitleTpl: '고객군 {n}칸 지형',
    briefL2NaTitle: '개정 담보 나눔과 시장 소식',
    briefL2DaTitle: '회사별 열린 종형 수',
    briefL2RaTitle: '치료 여정 다섯 단계',
    briefL2MaTitle: '영업 인사이트 다섯 분류',
    briefHospShort: '입원',
    briefSurgShort: '수술만',
    briefTimeOver5: '5년+',
    briefRevNew: '신설',
    briefRevChg: '변경',
    briefRevEnd: '종료',
    briefNewsNode: '시장 소식',
    briefGateUnknownSym: '?',
    briefGateOpenUnit: '종 열림',
    briefOursGroup: '우체국',
    briefSegSameNote: '지금 조건이 이미 이 고객군입니다.',
    briefSegWillChangeTpl: '누르면 조건 줄이 {target} 바뀝니다.',
    briefSegChangedToastTpl: '조건을 바꿨습니다: {sum}',
    briefStepUnit: '개',
    briefInsUnit: '건',
    briefListSub: '다섯 줄의 차례는 탭 차례와 같습니다',
    briefListTitle: '분석 요약 전체 문장',
    briefOffCondTpl: '지금 조건({cond})은 대표 조건({ref})과 다릅니다. 메달 숫자는 대표 조건 기준입니다.',
    briefApplySegBtn: '이 고객군으로 조건 바꾸기',
    briefLimitOutTpl: '지금 조건 {who}: {kind}의 가입나이({lo}~{hi}세) 밖입니다.',
    briefLimitInTpl: '지금 조건 {who}: 주계약 최대 가입금액 {max}만원({lo}~{hi}세 구간{extra}).',
    briefLimitPend: ', 검토 대기',
    briefLimitSameSex: ', 남녀 같음',
    briefEvCellsTitle: '칸의 수',
    briefEvRevTitle: '개정 변동',
    briefEvNewsTitleTpl: '시장 소식 {week}',
    briefEvGateValTitle: '기준 종형 값',
    briefEvLimitTblTpl: '나이 구간별 한도({sex})',
    briefEvNoLimit: '한도 자료 없음: 이 종형의 한도 표가 아직 없습니다.',
    briefEvNoSimpQ: '일반심사 종형이라 간편 고지 질문을 견주지 않았습니다.',
    briefEvPairTitle: '쌍과 담보의 수',
    briefEvCautionTpl: '단정 주의 {n}건',
    briefEvInsTitle: '다섯 분류',
    briefEvFirstTpl: '먼저 볼 것 {n}건',
    briefEvEmpty: '해당 항목이 없습니다.',
    briefEvGateOpenList: '열린 간편 종형',
    briefEvRevPairTpl: '{kind}: 신설 {n1}, 변경 {n2}, 종료 {n3}',
    briefEvNonAddPairTpl: '개정 짝 {c}개의 합은 {sum}건입니다(중복 포함).',
    briefEvNonAddStep: '쌍은 상대와 함께 가진 짝이고 담보 수는 우체국 단독 수라 서로 더하지 않습니다.',
    briefEqCellsTotal: '고객군',
    briefEqRevTotal: '달라진 담보',
    briefEqNewsTotal: '소식',
    briefEqPairTotal: '공통 담보',
    briefEqCmp: '견줌',
    briefEqWait: '검토 대기',
    briefEqPairUnit: '쌍',
    briefEqOurCov: '우체국 담보',
    briefEqOther: '기타',
    briefEqInsTotal: '인사이트',
    briefWonUnit: '만원',
    briefEvOnlyTitle: '우리 간편만 열리는 칸',
    briefEvOnlyRepTpl: '우리 대표 종형 {rep}. {peers}',
    briefEvNoneWord: '없음',
    briefEvMapScopeTpl: '고객군 지도({sex}, 갱신 유형 전체)로 셉니다.',
    briefEvHoldTitle: '검토 대기 요약',
    briefEvHoldWhyTpl: '사유별: {why}(중복 합 {sum}쌍).',
    briefEvAgeRange: '가입나이',
    briefEvRefLimitTpl: '대표 조건 {age}세 한도',
    briefEvGateDiff: '고지 질문 차이',
    briefEvDiffStruct: '구조 다름 상대',
    briefEvPlaceUnit: '곳',
    briefEvPendSuffix: ' (검토 대기)',
    briefEvInsSkipTpl: '검토 대기 등으로 뺀 포인트 {n}건은 세지 않았습니다.',
  };

  function cp(key, vars) {
    let s = key in COPY ? COPY[key] : key;
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll('{' + k + '}', String(v == null ? '' : v));
    return s;
  }

  const TAB_IDS = ['brief', 'market', 'gate', 'cover', 'insight'];
  const TAB_NAME = Object.fromEntries(TAB_IDS.map((id, i) => [id, S['탭'][i]]));
  const TAB_BY_NAME = Object.fromEntries(TAB_IDS.map((id, i) => [S['탭'][i], id]));
  const TAB_BRIEF_KEY = { market: '가', gate: '다', cover: '라', insight: '마' };
  // 회사 목록과 업권은 코드에 박지 않고 자료(S.회사, S.종형, D.orgs, S.지도)에서 읽는다
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
    if (sec || nm || !ORG_SECTOR[code]) ORG_SECTOR[code] = inferSector(code, nm || ORG_NAME[code], sec);
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
    for (const o of DD.orgs) registerOrg(o.code, o.name || o.short, o.sector || o['업권']);
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
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* */ } },
  };
  const LS_SKIN = 'postlife-c4-skin', LS_MOTION = 'postlife-c4-motion';

  // ---------- 글 도우미 (R1 이름 줄이기, R2 조사, R3 요약) ----------
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

  // ---------- 상태(sel = 2층 선택, sub = 3층 세부 선택, peerScope = 비교 범위) ----------
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
    sel: {},
    sub: {},
    skin: 'light',
    motion: 'on',
  };
  const listeners = { change: [], tab: [], select: [], sub: [] };
  const tabs = {};
  let booted = false;
  let condOpen = false;
  let scopeOpen = false;

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
    else out.cell = m['칸'][ri][ci];
    if (s.sex !== m['성별']) out.sexNote = cp('whySegSexTpl', { sex: sexText(s.sex), mapSex: sexText(m['성별']) });
    return out;
  }
  /** cellOf 의 반대: 지도 m 의 칸(ri, ci)을 가리키게 하는 조건 줄 값(고객군 탭과 브리핑이 함께 쓴다) */
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
    const hit = seg.find(g => s.age >= g.lo && g.age <= g.hi);
    const lo = seg.length ? seg[0].lo : null, hi = seg.length ? seg[seg.length - 1].hi : null;
    return { table: t, hit: hit || null, lo, hi };
  }
  function ctx(changed) {
    const base = S['기준별'][st.base];
    const pOrgs = activePeerOrgs();
    const pSet = new Set(pOrgs);
    const rawPeerIds = base ? base['맞붙는종형'] : [];
    const filteredPeerIds = st.peerScope === 'all' ? rawPeerIds : rawPeerIds.filter(id => pSet.has((vinfo(id) || {})['기관코드']));
    return {
      S, D: DD,
      st: { ...st, peerPick: st.peerPick.slice(), sel: { ...st.sel }, sub: { ...st.sub } },
      changed: changed || new Set(),
      baseId: st.base, base, baseInfo: vinfo(st.base),
      peerIds: filteredPeerIds, peers: filteredPeerIds.map(vinfo),
      allPeerIds: rawPeerIds,
      peerScope: st.peerScope, activePeerOrgs: pOrgs, activeOrgs: ['EPOST'].concat(pOrgs),
      seg: cellOf(), limit: limitOf(), ref: REF, isRef: isRefCond(),
      ui: UI, txt: TXT, t: cp,
    };
  }
  const isRefCond = () => st.age === REF['나이'] && st.sex === REF['성별'] && st.since === REF['이력'] && !st.surg;

  function set(patch, opts = {}) {
    const changed = new Set();
    for (const [k, v] of Object.entries(patch)) {
      if (!(k in st)) continue;
      if ((k === 'sel' || k === 'sub') && (!v || typeof v !== 'object')) continue;
      if (JSON.stringify(st[k]) !== JSON.stringify(v)) { st[k] = v; changed.add(k); }
    }
    if (!changed.size) return;
    if (changed.has('since') && st.since == null && st.surg) { st.surg = false; changed.add('surg'); }
    if (changed.has('skin')) applySkin();
    if (changed.has('motion')) applyMotion();
    const group = groupOf(changed);
    // 조건을 바꾸면 펼쳐진 조건 줄을 다시 접는다(나이 입력 타이핑 도중과 비교 범위 팝오버 조작은 제외)
    if ((group.cond || group.base || group.renewal) && condOpen && !opts.keepCond) setCondOpen(false);
    if (opts.push !== false && booted && (group.cond || group.base || group.renewal || group.peer || changed.has('tab'))) pushHistory(changed);
    if (changed.has('tab')) showTab(st.tab, opts);
    if (group.cond || group.base || group.renewal || group.peer) notify(changed, opts);
  }
  function groupOf(c) {
    return {
      cond: ['age', 'sex', 'since', 'surg'].some(k => c.has(k)),
      base: c.has('base'),
      renewal: c.has('renewal'),
      peer: c.has('peerScope') || c.has('peerPick'),
    };
  }
  function on(ev, fn) { (listeners[ev] = listeners[ev] || []).push(fn); }
  function emit(ev, ...a) { for (const fn of (listeners[ev] || [])) { try { fn(...a); } catch (e) { console.error(e); } } }

  // ---------- 브라우저 기록(#t=...&p=2층&u=3층 포함, 뒤로 가기로 한 층씩 올라간다) ----------
  function encodeHash() {
    const p = new URLSearchParams();
    p.set('t', st.tab); p.set('a', String(st.age)); p.set('s', st.sex);
    p.set('h', st.since == null ? '-' : String(st.since)); p.set('o', st.surg ? '1' : '0');
    p.set('b', st.base); p.set('r', st.renewal || '-');
    if (st.peerScope && st.peerScope !== 'all') {
      p.set('ps', st.peerScope);
      if (st.peerScope === 'custom') p.set('pp', (st.peerPick || []).join('.'));
    }
    if (st.sel[st.tab] != null) p.set('p', String(st.sel[st.tab]));
    if (st.sub[st.tab] != null) p.set('u', String(st.sub[st.tab]));
    return '#' + p.toString();
  }
  function decodeHash(h) {
    const p = new URLSearchParams(String(h || '').replace(/^#/, ''));
    const out = {};
    if (TAB_IDS.includes(p.get('t'))) out.tab = p.get('t');
    const a = parseInt(p.get('a'), 10); if (a >= 1 && a <= 100) out.age = a;
    if (p.get('s') === 'M' || p.get('s') === 'F') out.sex = p.get('s');
    if (p.has('h')) { const hv = p.get('h'); if (hv === '-') out.since = null; else { const n = parseFloat(hv); if (SINCE_OPTS.some(o => o.v === n)) out.since = n; } }
    if (p.has('o')) out.surg = p.get('o') === '1';
    if (BASES.some(b => b['종형ID'] === p.get('b'))) out.base = p.get('b');
    if (p.has('r')) { const r = p.get('r'); out.renewal = r === '-' ? null : (r === '갱신' || r === '비갱신' ? r : null); }
    if (PEER_SCOPES.includes(p.get('ps'))) {
      out.peerScope = p.get('ps');
      if (out.peerScope === 'custom' && p.has('pp')) {
        const raw = p.get('pp') ? p.get('pp').split('.') : [];
        out.peerPick = PEER_ORGS.filter(o => raw.includes(o));
      }
    } else if (p.has('ps')) {
      out.peerScope = 'all';
    }
    const pick = p.has('p') ? p.get('p') : null;
    const sub = p.has('u') ? p.get('u') : null;
    return { patch: out, pick, sub };
  }
  let lastPush = { t: 0, k: '' };
  function pushHistory(changed) {
    const kind = [...changed].sort().join(',');
    const now = Date.now();
    const url = encodeHash();
    const isLayer = changed.has('pick') || changed.has('sub') || changed.has('tab');
    const rapid = !isLayer && now - lastPush.t < 900 && lastPush.k === kind;
    try {
      if (rapid) history.replaceState({ c4: 1 }, '', url); else history.pushState({ c4: 1 }, '', url);
    } catch (e) { /* */ }
    lastPush = { t: now, k: kind };
  }
  window.addEventListener('popstate', () => {
    closeHelp(false); hideHudTip();
    const d = decodeHash(location.hash);
    const targetTab = d.patch.tab || st.tab;
    if (d.pick != null) st.sel[targetTab] = d.pick; else delete st.sel[targetTab];
    if (d.sub != null && d.pick != null) st.sub[targetTab] = d.sub; else delete st.sub[targetTab];
    const prevTab = st.tab;
    set(d.patch, { push: false, keepCond: false });
    if (st.tab === prevTab) applyLayerView(false);
  });

  // ---------- 화면 모드 ----------
  const mode = () => (innerWidth >= 1600 ? 'wide' : innerWidth >= 1000 ? 'push' : 'sheet');
  const motionOn = () => st.motion === 'on';

  // ---------- 그림 부품 ----------
  const IC = {
    chevR: '<svg width="8" height="14" viewBox="0 0 8 14" aria-hidden="true"><path d="M1.2 1.2L6.8 7l-5.6 5.8" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
    chevL: '<svg width="8" height="14" viewBox="0 0 8 14" aria-hidden="true"><path d="M6.8 1.2L1.2 7l5.6 5.8" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
    chevD: '<svg width="12" height="8" viewBox="0 0 12 8" aria-hidden="true"><path d="M1 1.2l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
    better: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 .8L9.6 9.2H.4Z" fill="currentColor"/></svg>',
    only: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 .4L9.6 5 5 9.6.4 5Z" fill="currentColor"/></svg>',
    worse: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M.4 .8H9.6L5 9.2Z" fill="currentColor"/></svg>',
    same: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1 3.4h8M1 6.6h8" stroke="currentColor" stroke-width="1.6"/></svg>',
    diff: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1 3h7.2M6 1l2.2 2L6 5M9 7H1.8M4 5 1.8 7 4 9" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>',
    none: '<svg viewBox="0 0 10 10" aria-hidden="true"><rect x=".8" y=".8" width="8.4" height="8.4" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="1.6 1.4"/><path d="M2.4 5h5.2" stroke="currentColor" stroke-width="1.4"/></svg>',
    unknown: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M3 3.4C3 2 4 1.2 5.1 1.2 6.3 1.2 7.1 2 7.1 3c0 1.6-2.1 1.6-2.1 3.3" fill="none" stroke="currentColor" stroke-width="1.4"/><rect x="4.3" y="7.6" width="1.4" height="1.4" fill="currentColor"/></svg>',
    lock: '<svg width="12" height="14" viewBox="0 0 12 14" aria-hidden="true"><path d="M3 6V4a3 3 0 0 1 6 0v2" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="1" y="6" width="10" height="7.2" fill="currentColor"/></svg>',
    copy: '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x="4" y="4" width="9" height="9" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M1 10V1h9" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
    print: '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 5V1h7v4M3.5 10.5H1V5h12v5.5h-2.5" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="3.5" y="8" width="7" height="5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
    grid: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><path d="M0 0h3v3H0zM4 0h3v3H4zM8 0h3v3H8zM0 4h3v3H0zM4 4h3v3H4zM8 4h3v3H8zM0 8h3v3H0zM4 8h3v3H4zM8 8h3v3H8z" fill="currentColor"/></svg>',
    pin: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><rect x=".75" y=".75" width="9.5" height="9.5" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="3.5" y="3.5" width="4" height="4" fill="currentColor"/></svg>',
    open: '<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><rect x=".75" y=".75" width="8.5" height="8.5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
    check: '<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><rect x=".75" y=".75" width="8.5" height="8.5" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="1.6 1.3"/></svg>',
    hatch: '<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><rect x=".5" y=".5" width="9" height="9" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="1.6 1.3"/><path d="M0 7 7 0M3 10 10 3" stroke="currentColor" stroke-width="1"/></svg>',
    arrow: '<svg width="14" height="10" viewBox="0 0 14 10" aria-hidden="true"><path d="M0 5h12M8.5 1.2 12.3 5 8.5 8.8" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
    now: '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true"><circle cx="5.5" cy="5.5" r="4.6" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="5.5" cy="5.5" r="1.9" fill="currentColor"/></svg>',
    legend: '<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><rect x="1" y="1.5" width="3" height="3" fill="currentColor"/><path d="M6 3h5M6 9h5" stroke="currentColor" stroke-width="1.4"/><circle cx="2.5" cy="9" r="1.6" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>',
  };

  const VD = {
    better: ['vd-better', 'vdBetter'],
    only: ['vd-only', 'vdOnly'],
    worse: ['vd-worse', 'vdWorse'],
    same: ['vd-same', 'vdSame'],
    diff: ['vd-diff', 'vdDiff'],
    none: ['vd-none', 'vdNone'],
    unknown: ['vd-unknown', 'vdUnknown'],
  };
  function verdict(kind, text, title) {
    const v = VD[kind] || VD.unknown;
    return `<span class="vd ${v[0]}"${title ? ` title="${esc(title)}"` : ''}>${IC[kind] || ''}<span>${esc(text || cp(v[1]))}</span></span>`;
  }
  const FLAG_TEXT = cp('flagDefault');
  const flag = (text = FLAG_TEXT) => `<span class="flag" role="img" aria-label="${esc(text)}" title="${esc(text)}"><i></i></span>`;
  const flagText = (text = FLAG_TEXT) => `<span class="flag-t"><span class="tri" aria-hidden="true"><i></i></span>${esc(text)}</span>`;
  const scope = (kind, title) => kind === 'all'
    ? `<span class="scb scb-all" title="${esc(title || cp('scopeAllHint'))}">${IC.grid}${esc(cp('scopeAll'))}</span>`
    : kind === 'now'
      ? `<span class="scb scb-now" title="${esc(title || cp('scopeNowHint'))}">${IC.now}${esc(cp('scopeNow'))}</span>`
      : `<span class="scb scb-base" title="${esc(title || cp('scopeBaseHint'))}">${IC.pin}${esc(cp('scopeBase'))}</span>`;
  const tag = (t, title, cls = '') => `<span class="tag ${cls}"${title ? ` title="${esc(title)}"` : ''}>${esc(t)}</span>`;
  function name(full, opts = {}) {
    const r = shortName(full, opts);
    return r.changed ? `<span class="nm" title="${esc(r.full)}">${esc(r.short)}</span>` : `<span class="nm">${esc(r.full)}</span>`;
  }
  /** 제목 묶음: 한 줄 층 경로(.lpath), 큰 제목, 좌우 꺾쇠 달린 탭 자리 표시(< · ━ · >) */
  function title(tabId, kicker, text) {
    const i = TAB_IDS.indexOf(tabId);
    const dots = TAB_IDS.map((_, j) => `<i${j === i ? ' class="on"' : ''}></i>`).join('');
    return `<div class="ttl"><nav class="lpath" aria-label="${esc(cp('pathAria'))}"><span class="lp-cur">${esc(TAB_NAME[tabId])}</span></nav><h1 class="ttl-t">${esc(text || TAB_NAME[tabId])}</h1>
      <div class="ttl-i" role="group" aria-label="${esc(TAB_NAME[tabId])}"><button type="button" class="ttl-step" data-tab-step="-1" aria-label="${esc(cp('tabPrevAria'))}">${IC.chevL}</button>${dots}<button type="button" class="ttl-step" data-tab-step="1" aria-label="${esc(cp('tabNextAria'))}">${IC.chevR}</button></div></div>`;
  }
  const big = (n, d, unit) => `<span class="big"><span class="n">${esc(fmt(n))}</span>${d != null ? `<span class="d">/${esc(fmt(d))}</span>` : ''}${unit ? `<span class="u">${esc(unit)}</span>` : ''}</span>`;
  function ring({ v = 0, max = 1, size = 72, lead = false, segs = null, pct = null, sel = false, label = '' } = {}) {
    const frac = max > 0 ? Math.max(0, Math.min(1, v / max)) : 0;
    const parts = segs || [{ v, cls: '' }];
    let acc = 0, arcs = '';
    for (const s of parts) {
      const f = max > 0 ? Math.max(0, s.v / max) : 0;
      if (f > 0) arcs += `<circle class="arc ${s.cls || ''}" r="40" fill="none" stroke-width="4.5" pathLength="100" stroke-dasharray="${(f * 100).toFixed(2)} 100" stroke-dashoffset="${(-acc * 100).toFixed(2)}" transform="rotate(-90)" data-to="${(f * 100).toFixed(2)}"/>`;
      acc += f;
    }
    let tks = '';
    for (let i = 0; i < 72; i++) {
      const a = i / 72; if (a < frac - 1e-6) continue;
      const t = a * Math.PI * 2 - Math.PI / 2, c = Math.cos(t), s = Math.sin(t);
      tks += `<line x1="${(c * 37).toFixed(2)}" y1="${(s * 37).toFixed(2)}" x2="${(c * 43).toFixed(2)}" y2="${(s * 43).toFixed(2)}"/>`;
    }
    const diag = lead || sel ? '<path class="diag" d="M-55-55l11 11M55-55l-11 11M-55 55l11-11M55 55l-11-11" stroke-width="2.2" fill="none"/>' : '';
    const disc = sel ? '<circle class="disc" r="35"/>' : '';
    const txt = pct != null ? `<text class="pct" text-anchor="middle" dominant-baseline="central" y="1">${esc(pct)}</text>` : '';
    return `<svg class="ring${sel ? ' sel' : ''}${lead ? ' lead' : ''}" width="${size}" height="${size}" viewBox="-60 -60 120 120" role="img" aria-label="${esc(label)}">
      <circle class="trk" r="40" fill="none" stroke-width="1"/>${disc}<g class="tks" stroke-width="1.6">${tks}</g>${arcs}${diag}${txt}</svg>`;
  }
  function drawRings(root) {
    if (!motionOn() || !root) return;
    const arcs = $$('.ring .arc', root);
    arcs.forEach(a => { a.style.transition = 'none'; a.style.strokeDasharray = '0 100'; });
    void root.getBoundingClientRect();
    requestAnimationFrame(() => requestAnimationFrame(() => arcs.forEach(a => { a.style.transition = ''; a.style.strokeDasharray = `${a.dataset.to} 100`; })));
  }
  const hbar = (v, max, cls = '') => `<span class="hbar" role="img" aria-label="${esc(fmt(v))}/${esc(fmt(max))}"><i class="${cls}" style="width:${max > 0 ? Math.max(0, Math.min(100, v / max * 100)).toFixed(1) : 0}%"></i></span>`;
  const btn = (text, o = {}) => `<button type="button" class="btn${o.main ? ' btn-main' : ''}${o.sm ? ' sm' : ''}${o.ghost ? ' ghost' : ''}${o.cls ? ' ' + o.cls : ''}" ${o.attrs || ''}>${o.icon ? IC[o.icon] || '' : ''}<span>${esc(text)}</span>${o.chev ? IC.chevR : ''}</button>`;
  function table({ id = '', head = [], rows = [], num = [], caption = '', pick = null } = {}) {
    const th = head.map((h, i) => `<th scope="col"${num.includes(i) ? ' class="v"' : ''}>${h}</th>`).join('');
    const tr = rows.map((r, ri) => {
      const k = pick ? pick(ri) : null;
      return `<tr${k != null ? ` class="pick" data-pick="${esc(k)}" tabindex="0"` : ''}>${r.map((c, i) => `<td${num.includes(i) ? ' class="v"' : ''}>${c}${k != null && i === r.length - 1 ? RCHEV : ''}</td>`).join('')}</tr>`;
    }).join('');
    return `<table class="tbl"${id ? ` id="${esc(id)}"` : ''}>${caption ? `<caption>${caption}</caption>` : ''}<thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`;
  }
  const RCHEV = `<span class="rchev" aria-hidden="true">${IC.chevR}</span>`;

  // ---------- 용어 물음표와 범례 팝오버 ----------
  const TERMS = {
    'scope-band': { titleKey: 'termScopeTitle', bodyKey: 'termScopeBody' },
    'ev-panel': { titleKey: 'termEvTitle', bodyKey: 'termEvBody' },
    'base-sel': { titleKey: 'termBaseTitle', bodyKey: 'termBaseBody' },
    'journey-grid': { titleKey: 'termJourneyTitle', bodyKey: 'termJourneyBody' },
    'caution-pending': { titleKey: 'termCautionTitle', bodyKey: 'termCautionBody' },
  };
  const LEGENDS = {};
  function registerLegend(key, titleKey, htmlFn) {
    LEGENDS[key] = { titleKey, htmlFn };
  }
  const help = (key, label) => {
    const t = TERMS[key];
    if (!t) return '';
    return `<button type="button" class="qhelp live no-print" data-help="${esc(key)}" aria-expanded="false" aria-controls="help-pop" aria-label="${esc((label || cp(t.titleKey)) + cp('helpSuffixAria'))}">?</button>`;
  };
  const legendBtn = (key = 'verdict', label) =>
    `<button type="button" class="btn sm ghost leg-btn live no-print" data-legend="${esc(key)}" aria-expanded="false" aria-controls="help-pop">${IC.legend}<span>${esc(label || cp('legendBtn'))}</span></button>`;

  const NOTE_HEAD = { '지도전제': 'noteHeadMap', '간편청약제한': 'noteHeadSimp', '수술만행': 'noteHeadSurg', '일반심사': 'noteHeadGen' };
  function notes(tabName) {
    const list = (S['주석'] || []).filter(n => Array.isArray(n['탭']) && n['탭'].includes(tabName));
    if (!list.length) return '';
    return `<div class="snotes" role="note" aria-label="${esc(tabName + cp('notesAriaSuffix'))}"><div class="snotes-h">${esc(cp('notesTitle'))}</div><ul class="snotes-l">${list.map(n => {
      const hk = NOTE_HEAD[n['열쇠']];
      return `<li>${hk ? `<b>${esc(cp(hk))}.</b>` : ''}${esc(n['글'])}${n['출처'] ? `<span class="snotes-src">(${esc(cp('notesSrcPrefix') + n['출처'])})</span>` : ''}</li>`;
    }).join('')}</ul></div>`;
  }

  function band({ id = '', kicker = '', title: t = '', help: hKey = '', sc = '', stats = [], eq: eqHtml = '', note = '' } = {}) {
    const stHtml = stats.map(s => `<div class="sb-st"${s.title ? ` title="${esc(s.title)}"` : ''}>
        <span class="big"><span class="n">${esc(fmt(s.n))}</span>${s.d != null ? `<span class="d">/${esc(fmt(s.d))}</span>` : ''}${s.u ? `<span class="u">${esc(s.u)}</span>` : ''}</span>
        <span class="sb-l">${esc(s.l)}</span>${s.bar ? hbar(s.bar[0], s.bar[1], s.bar[2] || '') : ''}</div>`).join('');
    return `<div class="sband"${id ? ` id="${esc(id)}"` : ''}>
      <div class="sb-t pillar tl"><i class="sb-tk" aria-hidden="true"></i><span class="k">${(Array.isArray(sc) ? sc : [sc]).filter(Boolean).map(x => scope(x)).join('')}${kicker ? `<span>${esc(kicker)}</span>` : ''}</span><h2><span>${esc(t)}</span>${hKey ? help(hKey, t) : ''}</h2></div>
      <div class="sb-s">${stHtml}</div>
      ${eqHtml || note ? `<div class="sb-f">${eqHtml}${note ? `<p class="note">${esc(note)}</p>` : ''}</div>` : ''}
    </div>`;
  }
  function eq({ total, parts = [], tail = '', nonAdd = '' }) {
    const p = parts.map(x => `<span class="nb">${esc(x.t)}</span> <span class="n">${esc(fmt(x.n))}</span>`).join(' <span class="op">+</span> ');
    return `<div class="eq">${total ? `<span class="nb">${esc(total.t)}</span> <span class="n">${esc(fmt(total.n))}</span> <span class="op">=</span> ` : ''}${p}${tail ? ` <span class="nb">${esc(tail)}</span>` : ''}</div>${nonAdd ? `<div class="nadd">${esc(nonAdd)}</div>` : ''}`;
  }
  const fadeBand = (html, o = {}) => `<div class="fade-band${o.slate ? ' slate' : ''}">${html}</div>`;
  const cells = list => `<div class="cqs" aria-hidden="true">${list.map(c => `<i class="cq ${c}"></i>`).join('')}</div>`;
  const MAP_CLS = { '우리 간편만 열림': 'm-only', '함께 열림': 'm-both', '우리 간편 닫힘': 'm-ours', '간편 모두 닫힘': 'm-all', '자료 없음': 'm-none' };
  const swatch = label => `<i class="cq ${MAP_CLS[label] || 'm-none'}" style="width:12px;height:12px;display:inline-block;vertical-align:-1px"></i>`;

  function chevSel({ label, options, value, onChange, w = '72px', num = false, id = '' }) {
    const el = document.createElement('div');
    el.className = 'chev-sel' + (num ? ' num' : '');
    el.style.setProperty('--w', w);
    el.setAttribute('role', 'group'); el.setAttribute('aria-label', label);
    if (id) el.id = id;
    el.innerHTML = `<button type="button" class="p" aria-label="${esc(label + cp('chevPrevSuffix'))}">${IC.chevL}</button><span class="v" aria-live="polite"></span><button type="button" class="n" aria-label="${esc(label + cp('chevNextSuffix'))}">${IC.chevR}</button>`;
    const vEl = $('.v', el), pB = $('.p', el), nB = $('.n', el);
    let cur = value;
    const idx = () => options.findIndex(o => JSON.stringify(o.v) === JSON.stringify(cur));
    el.set = v => {
      cur = v; const i = idx(); const o = options[i];
      vEl.textContent = o ? o.t : String(v);
      if (o && o.title) vEl.title = o.title; else vEl.removeAttribute('title');
      pB.disabled = i <= 0; nB.disabled = i < 0 || i >= options.length - 1;
    };
    const move = d => { const i = idx() + d; if (i < 0 || i >= options.length) return; el.set(options[i].v); onChange && onChange(options[i].v); };
    pB.addEventListener('click', () => move(-1));
    nB.addEventListener('click', () => move(1));
    el.addEventListener('keydown', e => { if (e.key === 'ArrowLeft') { move(-1); e.preventDefault(); } if (e.key === 'ArrowRight') { move(1); e.preventDefault(); } });
    el.set(value);
    return el;
  }
  function stepper({ label, value, min, max, unit = '', onChange, w = '44px' }) {
    const el = document.createElement('div');
    el.className = 'chev-sel num'; el.style.setProperty('--w', w);
    el.setAttribute('role', 'group'); el.setAttribute('aria-label', label);
    el.innerHTML = `<button type="button" class="p" aria-label="${esc(label + cp('stepDecSuffix'))}">${IC.chevL}</button><input type="text" inputmode="numeric" maxlength="3" aria-label="${esc(label)}" autocomplete="off"><span class="v" style="min-width:0;padding:0 6px 0 0;font:600 14px/1 var(--f-ko)">${esc(unit)}</span><button type="button" class="n" aria-label="${esc(label + cp('stepIncSuffix'))}">${IC.chevR}</button>`;
    const inp = $('input', el);
    let cur = value, timer = 0;
    el.set = v => { cur = v; inp.value = String(v); $('.p', el).disabled = v <= min; $('.n', el).disabled = v >= max; };
    const commit = (v, keepCond) => { v = Math.max(min, Math.min(max, v)); el.set(v); onChange && onChange(v, keepCond); };
    $('.p', el).addEventListener('click', () => commit(cur - 1, false));
    $('.n', el).addEventListener('click', () => commit(cur + 1, false));
    inp.addEventListener('input', () => {
      inp.value = inp.value.replace(/[^0-9]/g, '');
      clearTimeout(timer);
      const n = parseInt(inp.value, 10);
      if (n >= min && n <= max) timer = setTimeout(() => commit(n, true), 450);
    });
    inp.addEventListener('blur', () => { const n = parseInt(inp.value, 10); if (isNaN(n)) el.set(cur); else commit(n, false); if (condOpen) setCondOpen(false); });
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') { inp.blur(); }
      if (e.key === 'ArrowUp') { commit(cur + 1, true); e.preventDefault(); }
      if (e.key === 'ArrowDown') { commit(cur - 1, true); e.preventDefault(); }
    });
    el.set(value);
    return el;
  }

  const pageText = (doc, page) => (page != null && page !== '' ? `${doc || cp('docFallback')} ${page}${cp('pageSuffix')}` : `${doc || cp('docFallback')}${cp('pageMissingSuffix')}`);
  const PAGE_WHY = cp('pageWhy');

  const UI = { esc, fmt, t: cp, IC, verdict, flag, flagText, FLAG_TEXT, scope, tag, name, title, big, ring, drawRings, hbar, btn, table, RCHEV, band, eq, fadeBand, cells, MAP_CLS, swatch, chevSel, stepper, help, legendBtn, registerLegend, notes };
  const TXT = { josa, fixJosa, hasFinal, shortName, sameSummary, orgShort, orgSector, vname, vkind, vinfo, sinceText, sexText, stateWhy, pageText, PAGE_WHY, ORG_ORDER, PEER_ORGS, ORG_SHORT };

  // ---------- 0층: 접히는 조건 줄, 비교 범위 선택, 범위 띠 ----------
  const SINCE_OPTS = [{ v: null, t: cp('condNoHist') }].concat(
    S['지도']['전체']['행'].filter(r => r['종류'] === '입원').map(r => ({ v: r.since, t: r.since === 5 ? cp('condSince5') : r['이름'].replace(/^입원\s*/, '') })));
  const C = {};

  function peerScopeLabel() {
    if (st.peerScope === 'life') return cp('peerLifeGroup');
    if (st.peerScope === 'nonlife') return cp('peerNonLifeGroup');
    if (st.peerScope === 'custom') return cp('peerCustomShortTpl', { n: activePeerOrgs().length });
    return cp('peerAll');
  }

  function setCondOpen(open) {
    condOpen = !!open;
    const el = $('#cond');
    if (!el) return;
    el.classList.toggle('open', condOpen);
    const b = $('#cond-sum', el);
    if (b) {
      b.setAttribute('aria-expanded', String(condOpen));
      const act = $('.act-t', b);
      if (act) act.textContent = cp(condOpen ? 'condCloseBtn' : 'condOpenBtn');
    }
    placeEv(); placeGuides();
  }
  function setScopeOpen(open) {
    scopeOpen = !!open;
    const el = $('#scope'), b = $('#scope-tgl');
    if (el) el.hidden = !scopeOpen;
    if (b) b.setAttribute('aria-expanded', String(scopeOpen));
    placeEv(); placeGuides();
  }

  function renderCond() {
    const el = $('#cond');
    el.setAttribute('aria-label', cp('condAria'));
    el.innerHTML = `
      <div class="cond-bar">
        <button class="cond-sum" id="cond-sum" type="button" aria-expanded="false" aria-controls="cond-body">
          <span class="t"></span>
          <span class="act"><span class="act-t">${esc(cp('condOpenBtn'))}</span> ${IC.chevD}</span>
        </button>
        <span class="scope-chip">
          <button type="button" class="scope-tgl peer-tgl" id="peer-tgl" data-peer-pop="1" aria-expanded="false"><span id="peer-tgl-t"></span> ${IC.chevD}</button>
          <button type="button" class="scope-tgl" id="scope-tgl" aria-expanded="false" aria-controls="scope">${esc(cp('scopeBtn'))} ${IC.chevD}</button>${help('scope-band', cp('scopeTitle'))}
        </span>
      </div>
      <div class="cond-body" id="cond-body">
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
    $('#cond-sum', el).addEventListener('click', () => setCondOpen(!condOpen));
    $('#scope-tgl', el).addEventListener('click', () => setScopeOpen(!scopeOpen));
    syncCond();
  }

  function peerNamesShort(list) {
    if (!list.length) return '';
    if (list.length <= 2) return list.join(', ');
    return cp('peerRestTpl', { first: list[0], rest: list.length - 1 });
  }

  function condSummary() {
    const hist = st.since == null ? cp('condNoHist') : `${st.surg ? cp('condSurgOnly') : cp('condHospOrSurg')} ${sinceText(st.since)}`;
    const base = S['기준별'][st.base];
    const pSet = new Set(activePeerOrgs());
    const rawOrgs = base
      ? [...new Set(base['맞붙는종형'].map(v => (vinfo(v) || {})['기관코드']).filter(Boolean))]
      : [];
    const shownOrgs = st.peerScope === 'all' ? rawOrgs : rawOrgs.filter(o => pSet.has(o));
    const peers = peerNamesShort(shownOrgs.map(orgShort));
    return `${st.age}${cp('condAgeUnit')} ${sexText(st.sex)}, ${hist} / ${cp('condBasePrefix')} ${vkind(st.base)}${peers ? ` / ${cp('condPeerPrefix')} ${peers}` : ''}`;
  }
  function condSegOnly() {
    const hist = st.since == null ? cp('condNoHist') : `${st.surg ? cp('condSurgOnly') : cp('condHospOrSurg')} ${sinceText(st.since)}`;
    return `${st.age}${cp('condAgeUnit')} ${sexText(st.sex)}, ${hist}`;
  }
  function syncCond() {
    if (!C.age) return;
    C.age.set(st.age); C.sex.set(st.sex); C.base.set(st.base); C.ren.set(st.renewal);
    const sel = $('#c-since'); sel.value = String(SINCE_OPTS.findIndex(o => o.v === st.since));
    const sw = $('#c-surg'); sw.setAttribute('aria-checked', String(!!st.surg)); sw.disabled = st.since == null;
    sw.title = st.since == null ? cp('condSurgDisHint') : cp('condSurgHint');
    const base = S['기준별'][st.base];
    const allNames = base ? [...new Set(base['맞붙는종형'].map(v => orgShort((vinfo(v) || {})['기관코드'])))] : [];
    $('#c-peers').innerHTML = base ? `<span title="${esc(base['맞붙는종형'].map(vname).join(', '))}">${esc(peerNamesShort(allNames))}</span><span class="hint" style="margin-left:8px">${esc(cp('condPeersHint'))}</span>` : '';
    const pt = $('#peer-tgl-t');
    if (pt) pt.textContent = cp('peerBtnTpl', { s: peerScopeLabel() });
    $('#cond-sum .t').textContent = condSummary();
    $('#condmini').textContent = condSummary();
  }

  // ---------- 범위 띠(펼쳤을 때 두 줄 전체 표시) ----------
  const STATE_IC = { '열림': IC.open, '닫힘': IC.lock, '심사로 확인': IC.check, '나이 자료 없음': IC.hatch, '질문 자료 없음': IC.hatch };
  function renderScope() {
    const el = $('#scope');
    el.setAttribute('aria-label', cp('scopeAria'));
    const base = S['기준별'][st.base];
    if (!base) { el.innerHTML = ''; return; }
    const r = base['범위'];
    const bi = vinfo(st.base);
    const pSet = new Set(activePeerOrgs());
    const relPeers = st.peerScope === 'all' ? r['상대'] : r['상대'].filter(p => pSet.has((vinfo(p['종형ID']) || {})['기관코드']));
    const peers = relPeers.slice(0, 3).map(p => {
      const v = vinfo(p['종형ID']);
      const why = p['머리말'] != null ? S['글'][p['머리말']] : '';
      const sd = (why.split(` / ${cp('scopeDiffStruct')}: `)[1] || '');
      return `<span class="it"><span title="${esc(v ? v['전체이름'] : '')}">${esc(vname(p['종형ID']))}</span> <span class="d">${esc(v ? v['적용시작일'] : '')}</span>${p['구조다름'] ? ' ' + tag(cp('scopeDiffStruct'), sd ? cp('scopeDiffStruct') + ': ' + sd : cp('scopeDiffStructHint')) : ''}</span>`;
    }).join('') + (relPeers.length > 3 ? `<span class="it">+${fmt(relPeers.length - 3)}</span>` : '');
    const line1 = `<div class="scope-l"><span class="k">${esc(cp('scopeTitle'))}</span>
      <span class="it"><b style="font-weight:600" title="${esc(bi ? bi['전체이름'] : '')}">${esc(vname(st.base))}</b> <span class="d">${esc(bi ? bi['적용시작일'] : '')}</span></span>
      <span class="it" aria-label="${esc(cp('scopeVsAria'))}">${IC.arrow}</span>${peers}
      <span class="it">${esc(cp('scopePairTpl', { total: fmt(r['비교쌍']), wait: fmt(r['뺀비교쌍']) }))}</span>
      ${scope('base')}</div>`;
    const g = cellOf();
    let line2;
    if (!g.cell) {
      line2 = `<div class="scope-l"><span class="k">${esc(cp('scopeNowSeg'))}</span><span class="it">${esc(condSegOnly())}</span><span class="why">${esc(g.reason)}</span></div>`;
    } else {
      const c = g.cell;
      const shownOrgs = activeOrgs().filter(o => o in c['회사']);
      const states = shownOrgs.slice(0, 4).map(o => {
        const s = c['회사'][o];
        return `<span class="it">${esc(orgShort(o))} <span style="display:inline-flex;align-items:center;gap:4px">${STATE_IC[s] || ''}${esc(s)}</span></span>`;
      }).join('') + (shownOrgs.length > 4 ? `<span class="it">+${fmt(shownOrgs.length - 4)}</span>` : '');
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
    el.hidden = !scopeOpen;
    el.innerHTML = fadeBand(line1 + line2);
  }

  // ---------- 탭, 층 경로(.lpath), 본문 ----------
  function renderTabs() {
    const nav = $('#tabs');
    nav.setAttribute('aria-label', cp('tabsAria'));
    nav.innerHTML = TAB_IDS.map(id => `<button class="tab" type="button" role="tab" id="tab-${id}" aria-controls="view-${id}" aria-selected="false" tabindex="-1" data-tab="${id}"><span>${esc(TAB_NAME[id])}</span></button>`).join('');
    nav.addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) set({ tab: b.dataset.tab }); });
    nav.addEventListener('keydown', e => {
      const i = TAB_IDS.indexOf(st.tab);
      let j = -1;
      if (e.key === 'ArrowRight') j = (i + 1) % TAB_IDS.length;
      if (e.key === 'ArrowLeft') j = (i + TAB_IDS.length - 1) % TAB_IDS.length;
      if (e.key === 'Home') j = 0;
      if (e.key === 'End') j = TAB_IDS.length - 1;
      if (j >= 0) { e.preventDefault(); set({ tab: TAB_IDS[j] }); $('#tab-' + TAB_IDS[j]).focus(); }
    });
    const main = $('#main');
    for (const id of TAB_IDS) {
      const sec = document.createElement('section');
      sec.className = 'view'; sec.id = 'view-' + id; sec.hidden = true;
      sec.setAttribute('role', 'tabpanel'); sec.setAttribute('aria-labelledby', 'tab-' + id); sec.dataset.tab = id;
      const t = tabs[id];
      sec.innerHTML = `<header class="vhead">${title(id, t ? t.kicker : '', TAB_NAME[id])}<div class="vhead-aside"></div></header><div class="vbody"></div>`;
      main.appendChild(sec);
    }
  }
  function viewOf(id) { return document.getElementById('view-' + id); }

  /** 현재 탭의 한 줄 경로(1층: 탭 이름, 2층: 탭 > 항목, 3층: 탭 > 항목 > 세부)를 갱신한다 */
  function syncPath(id = st.tab) {
    const sec = viewOf(id); if (!sec) return;
    const nav = $('.lpath', sec); if (!nav) return;
    const t = tabs[id];
    const l2 = st.sel[id], l3 = st.sub[id];
    let parts = [TAB_NAME[id]];
    if (t && t.path) {
      try {
        const custom = t.path(ctx());
        if (Array.isArray(custom) && custom.length) parts = custom;
      } catch (e) { console.error(e); }
    } else if (l2 != null) {
      const ttl = $('#ev-t') ? $('#ev-t').textContent : String(l2);
      parts = [TAB_NAME[id], ttl];
    }
    nav.innerHTML = parts.map((label, idx) => {
      const last = idx === parts.length - 1;
      if (last) return `<span class="lp-cur">${esc(label)}</span>`;
      return `<button type="button" class="lp-b" data-layer-to="${idx + 1}">${esc(label)}</button><span class="lp-sep" aria-hidden="true">&gt;</span>`;
    }).join('');
  }

  function renderTab(id, c, why) {
    const t = tabs[id]; const sec = viewOf(id);
    if (!sec) return;
    const body = $('.vbody', sec), aside = $('.vhead-aside', sec);
    if (!t) { body.innerHTML = `<div class="panel placeholder">${esc(cp('tabMissing'))}</div>`; return; }
    try {
      t.render(body, Object.assign(c || ctx(), { aside, view: sec, why: why || 'render' }));
    } catch (e) {
      console.error(e);
      body.innerHTML = `<div class="panel placeholder">${esc(cp('tabErrorPrefix') + e.message)}</div>`;
    }
    t._dirty = false;
    remark(id);
    syncPath(id);
  }

  function applyLayerView(animate) {
    const id = st.tab;
    const t = tabs[id];
    if (t && t.onLayer) {
      const sec = viewOf(id);
      try { t.onLayer($('.vbody', sec), Object.assign(ctx(), { aside: $('.vhead-aside', sec), view: sec }), animate); } catch (e) { console.error(e); }
    }
    remark(id);
    const key = st.sel[id], subKey = st.sub[id];
    if (key != null && t) {
      if (subKey != null && t.pickSub) showSubPick(key, subKey, animate);
      else if (t.pick) showPick(key, animate);
      else showDefaultEv(animate);
      if (mode() !== 'wide' && EV.open) sheetPad();
    } else {
      showDefaultEv(animate);
      if (mode() !== 'wide') hideEv();
    }
    syncPath(id);
    placeGuides();
  }

  function showTab(id, opts = {}) {
    for (const x of TAB_IDS) {
      const b = $('#tab-' + x), v = viewOf(x), on = x === id;
      if (b) { b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1; if (on && mode() === 'sheet') b.scrollIntoView({ block: 'nearest', inline: 'nearest' }); }
      if (v) v.hidden = !on;
    }
    const t = tabs[id];
    if (t && (t._dirty || !t._drawn)) { renderTab(id, ctx(new Set(['tab'])), 'tab'); t._drawn = true; }
    const v = viewOf(id);
    if (t && t.enter) { try { t.enter($('.vbody', v), ctx(new Set(['tab']))); } catch (e) { console.error(e); } }
    if (v) drawRings(v);
    if (v && motionOn()) { v.classList.remove('entering'); void v.offsetWidth; v.classList.add('entering'); setTimeout(() => v.classList.remove('entering'), 700); }
    const key = st.sel[id], subKey = st.sub[id];
    if (key != null && t) {
      if (subKey != null && t.pickSub) showSubPick(key, subKey, false);
      else if (t.pick) showPick(key, false);
      else showDefaultEv(false);
    } else {
      showDefaultEv(false);
      if (mode() !== 'wide') hideEv();
    }
    syncPath(id);
    placeGuides();
    if (opts.scroll !== false && booted) {
      const top = $('#work').getBoundingClientRect().top + scrollY - (parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--head-h')) || 66) - 12;
      if (scrollY > top) scrollTo({ top, behavior: 'auto' });
    }
    emit('tab', id);
  }

  function notify(changed, opts = {}) {
    syncCond(); renderScope(); placeEv();
    const c = ctx(changed);
    for (const id of TAB_IDS) {
      const t = tabs[id]; if (!t) continue;
      if (id === st.tab) {
        let done = false;
        if (t.update) { try { done = t.update($('.vbody', viewOf(id)), Object.assign(c, { aside: $('.vhead-aside', viewOf(id)), view: viewOf(id) })) === true; } catch (e) { console.error(e); } }
        if (!done) renderTab(id, c, 'change');
        else { remark(id); syncPath(id); }
      } else t._dirty = true;
    }
    const key = st.sel[st.tab], subKey = st.sub[st.tab];
    const t = tabs[st.tab];
    if (key != null && t) {
      if (subKey != null && t.pickSub) showSubPick(key, subKey, false);
      else if (t.pick) showPick(key, false);
      else showDefaultEv(false);
    } else showDefaultEv(false);
    syncPath(st.tab);
    emit('change', c, opts);
  }

  // ---------- 고르기(2층, 3층)와 근거 기둥("고른 것만, 평소엔 결론 한 문장") ----------
  const EV = { open: false };
  function setEvBox(spec, animate) {
    const k = $('#ev-k'), t = $('#ev-t'), b = $('#ev-b'), body = $('#ev-body');
    k.textContent = spec.kicker || cp('evKickerPick');
    t.textContent = spec.title || '';
    b.innerHTML = (spec.badges || []).join('');
    body.innerHTML = typeof spec.body === 'string' ? spec.body : '';
    if (spec.body && typeof spec.body !== 'string') body.appendChild(spec.body);
    body.scrollTop = 0;
    if (animate && motionOn()) { const box = $('.ev-in'); box.classList.remove('ev-anim'); void box.offsetWidth; box.classList.add('ev-anim'); }
    if (spec.after) { try { spec.after(body); } catch (e) { console.error(e); } }
  }
  function showEv(spec, o = {}) {
    setEvBox(spec, o.animate !== false);
    if (o.open !== false && mode() !== 'wide') openEv();
  }
  function openEv() {
    if (mode() === 'wide') return;
    if (!EV.open) { EV.open = true; document.body.classList.add('ev-open'); }
    sheetPad();
  }
  function hideEv() {
    if (!EV.open) return;
    EV.open = false; document.body.classList.remove('ev-open');
    sheetPad();
  }
  function sheetPad() {
    const h = EV.open && mode() === 'sheet' ? $('#ev').offsetHeight : 0;
    document.documentElement.style.setProperty('--sheet-h', h + 'px');
  }

  /** 아무것도 고르지 않았을 때는 그 탭의 결론 한 문장만 보인다 */
  function defaultEvSpec() {
    const t = tabs[st.tab];
    if (t && t.defaultEv) {
      try { const spec = t.defaultEv(ctx()); if (spec) return spec; } catch (e) { console.error(e); }
    }
    return coreDefaultEv();
  }
  function showDefaultEv(animate) { setEvBox(defaultEvSpec(), animate); }
  function coreDefaultEv() {
    const base = S['기준별'][st.base];
    const bk = TAB_BRIEF_KEY[st.tab];
    let sent = '';
    let sc = 'base';
    if (base) {
      if (bk) {
        const row = (base['브리핑'] || []).find(x => x['줄'] === bk);
        if (row) { sent = row['문장']; sc = row['범위'] === '전체 고객군' ? 'all' : 'base'; }
      }
      if (!sent && base['범위']) sent = String(base['범위']['문장'] || '').split(/(?<=\.)\s+/)[0] || base['범위']['문장'];
    }
    return {
      kicker: cp('evKickerDefault'),
      title: TAB_NAME[st.tab],
      badges: [scope(sc)],
      body: `<div class="ev-sec"><p>${esc(sent)}</p></div>`,
    };
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

  function remark(id) {
    const v = viewOf(id); if (!v) return;
    const key = st.sel[id], subKey = st.sub[id];
    for (const el of $$('[data-pick]', v)) {
      const on = key != null && el.dataset.pick === String(key);
      el.classList.toggle('is-sel', on);
      const hit = el.matches('button') ? el : $('.lrow-hit', el);
      if (hit) hit.setAttribute('aria-pressed', String(on));
    }
    for (const el of $$('[data-sub-pick]', v)) {
      const on = subKey != null && el.dataset.subPick === String(subKey);
      el.classList.toggle('is-sub-sel', on);
      if (el.matches('button')) el.setAttribute('aria-pressed', String(on));
    }
    fitSel(v);
  }

  const SEL_SHARE = { wide: 0.021, push: 0.017, sheet: 0.016 };
  const SEL_EXTRA = 76;
  function fitSel(root) {
    root = root || viewOf(st.tab);
    if (!root) return;
    const budget = SEL_SHARE[mode()] * innerWidth * innerHeight;
    for (const el of $$('.is-sel', root)) {
      let bars;
      if (el.matches('tr')) {
        const blk = getComputedStyle(el).display === 'block';
        bars = blk ? [el.querySelector('td') || el] : [el];
      } else if (el.matches('.selbar')) bars = [el];
      else bars = $$('.selbar', el);
      for (const b of bars) {
        const r = b.getBoundingClientRect();
        if (!r.height) continue;
        const w = r.width + 24;
        const L = Math.max(8, Math.min(w + 120, Math.floor(budget / r.height - SEL_EXTRA)));
        b.style.setProperty('--sel-red', L >= w ? `${Math.ceil(w + 120)}px` : `${L}px`);
      }
    }
  }

  function showPick(key, animate) {
    const t = tabs[st.tab];
    let spec = null;
    try { spec = t && t.pick ? t.pick(String(key), ctx()) : null; } catch (e) { console.error(e); }
    if (!spec) { delete st.sel[st.tab]; delete st.sub[st.tab]; remark(st.tab); showDefaultEv(animate); return false; }
    setEvBox(spec, animate);
    return true;
  }
  function showSubPick(key, subKey, animate) {
    const t = tabs[st.tab];
    let spec = null;
    try { spec = t && t.pickSub ? t.pickSub(String(key), String(subKey), ctx()) : null; } catch (e) { console.error(e); }
    if (!spec) { delete st.sub[st.tab]; remark(st.tab); return showPick(key, animate); }
    setEvBox(spec, animate);
    return true;
  }

  function select(key, o = {}) {
    if (key == null) return unselect(o);
    const same = st.sel[st.tab] === String(key) && st.sub[st.tab] == null;
    st.sel[st.tab] = String(key);
    delete st.sub[st.tab];
    if (o.push !== false && booted && !same) pushHistory(new Set(['pick']));
    const t = tabs[st.tab];
    if (t && t.onLayer) {
      const sec = viewOf(st.tab);
      try { t.onLayer($('.vbody', sec), Object.assign(ctx(), { aside: $('.vhead-aside', sec), view: sec }), o.animate !== false); } catch (e) { console.error(e); }
    }
    remark(st.tab);
    const ok = showPick(key, o.animate !== false);
    syncPath(st.tab);
    if (ok && mode() !== 'wide' && o.open !== false) openEv();
    const el = $(`[data-pick="${CSS.escape(String(key))}"]`, viewOf(st.tab));
    if (el && o.reveal !== false) setTimeout(() => reveal(el), mode() === 'sheet' ? 260 : 0);
    placeGuides();
    emit('select', st.tab, String(key));
  }

  function selectSub(subKey, o = {}) {
    const key = st.sel[st.tab];
    if (key == null) return;
    if (subKey == null) {
      if (st.sub[st.tab] == null) return;
      delete st.sub[st.tab];
      if (o.push !== false && booted) pushHistory(new Set(['sub']));
      remark(st.tab);
      showPick(key, o.animate !== false);
      syncPath(st.tab);
      emit('sub', st.tab, null);
      return;
    }
    const same = st.sub[st.tab] === String(subKey);
    st.sub[st.tab] = String(subKey);
    if (o.push !== false && booted && !same) pushHistory(new Set(['sub']));
    remark(st.tab);
    const ok = showSubPick(key, subKey, o.animate !== false);
    syncPath(st.tab);
    if (ok && mode() !== 'wide' && o.open !== false) openEv();
    emit('sub', st.tab, String(subKey));
  }

  function unselect(o = {}) {
    const had = st.sel[st.tab] != null || st.sub[st.tab] != null;
    delete st.sel[st.tab];
    delete st.sub[st.tab];
    if (o.push !== false && booted && had) pushHistory(new Set(['pick']));
    const t = tabs[st.tab];
    if (t && t.onLayer) {
      const sec = viewOf(st.tab);
      try { t.onLayer($('.vbody', sec), Object.assign(ctx(), { aside: $('.vhead-aside', sec), view: sec }), o.animate !== false); } catch (e) { console.error(e); }
    }
    remark(st.tab);
    showDefaultEv(o.animate !== false);
    hideEv();
    syncPath(st.tab);
    placeGuides();
    emit('select', st.tab, null);
  }

  /** Esc나 경로 이동: 열린 팝오버 -> 조건/범위 -> 3층에서 2층 -> 2층에서 1층 순서로 한 단계 올라간다 */
  function stepUp() {
    if (closeHelp(true)) return true;
    if (condOpen) { setCondOpen(false); return true; }
    if (scopeOpen) { setScopeOpen(false); return true; }
    if (st.sub[st.tab] != null) { selectSub(null); return true; }
    if (st.sel[st.tab] != null || EV.open) { unselect(); return true; }
    return false;
  }

  function reveal(el) {
    if (!el) return;
    const r = el.getBoundingClientRect();
    const top = (parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--head-h')) || 66) + 12;
    const bottom = innerHeight - (EV.open && mode() === 'sheet' ? $('#ev').offsetHeight : 0) - 12;
    const sm = motionOn() ? 'smooth' : 'auto';
    if (r.top < top) scrollBy({ top: r.top - top, behavior: sm });
    else if (r.bottom > bottom) scrollBy({ top: Math.min(r.bottom - bottom, r.top - top), behavior: sm });
  }
  function go(tabId, o = {}) {
    if (!TAB_IDS.includes(tabId)) tabId = TAB_BY_NAME[tabId] || tabId;
    if (!TAB_IDS.includes(tabId)) return;
    set({ tab: tabId });
    const t = tabs[tabId];
    if (o.focus != null && t && t.focus) setTimeout(() => { try { t.focus(o.focus, $('.vbody', viewOf(tabId)), ctx()); } catch (e) { console.error(e); } }, 30);
  }

  // ---------- 복사와 인쇄 ----------
  function scopeLine() {
    const base = S['기준별'][st.base];
    const peers = base ? base['맞붙는종형'].map(vname).join(', ') : '';
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
    const headH = $('#head').offsetHeight;
    const main = $('#main').getBoundingClientRect();
    const ev = (mode() === 'sheet' ? $('#ev') : $('.ev-slot')).getBoundingClientRect();
    const narrow = mode() === 'sheet';
    const centers = [];
    centers.push(Math.round(main.left - 16));
    if (mode() === 'wide' || (EV.open && mode() === 'push')) centers.push(Math.round(main.right + (ev.left - main.right) / 2));
    const ttl = $('.view:not([hidden]) .ttl');
    if (ttl && !narrow) { const r = ttl.getBoundingClientRect(); if (r.width) centers.push(Math.round(r.right + 16)); }
    centers.push(Math.round((mode() === 'wide' || EV.open ? Math.max(ev.right, main.right) : main.right) + 16));
    let html = '';
    for (const c of centers) {
      if (c < 0 || c > W) continue;
      if (!narrow && mode() === 'wide') html += `<i class="gl" style="left:${c - 16}px"></i><i class="gl" style="left:${c + 16}px"></i>`;
      html += `<i class="gl c" style="left:${c}px"></i>`;
    }
    const yb = H - 90;
    html += `<i class="hl" style="top:${headH}px"></i><i class="hl" style="top:${yb}px"></i>`;
    for (const c of centers) if (c >= 0 && c <= W) html += `<i class="tk" style="left:${c}px;top:${headH}px"></i><i class="tk" style="left:${c}px;top:${yb}px"></i>`;
    const tb = $('#tab-' + st.tab);
    const tx = tb ? Math.round(tb.getBoundingClientRect().left + 7) : 0;
    html += `<i class="tk red" id="tk-red" style="left:${tx}px;top:${headH}px"></i>`;
    g.innerHTML = html;
  }

  function placeEv() {
    if (mode() === 'sheet') return;
    const headH = $('#head').offsetHeight;
    const top = Math.max(headH + 12, Math.round($('#work').getBoundingClientRect().top));
    document.documentElement.style.setProperty('--ev-top', top + 'px');
  }
  addEventListener('scroll', placeEv, { passive: true });

  // ---------- 스킨, 움직임 ----------
  function applySkin() {
    document.documentElement.dataset.theme = st.skin;
    const b = $('#skin'); if (b) { b.textContent = st.skin === 'dark' ? cp('skinLight') : cp('skinDark'); b.setAttribute('aria-pressed', String(st.skin === 'dark')); }
    store.set(LS_SKIN, st.skin);
  }
  function applyMotion() {
    document.documentElement.dataset.motion = st.motion;
    const b = $('#motion'); if (b) { b.innerHTML = `${esc(cp('motionWord'))} <b>${esc(st.motion === 'on' ? cp('motionOn') : cp('motionOff'))}</b>`; b.setAttribute('aria-pressed', String(st.motion === 'on')); }
    store.set(LS_MOTION, st.motion);
  }
  const asofText = () => String(S['자료시각'] || '').replace('T', ' ').slice(0, 16);

  // ---------- 용어 물음표, 범례 팝오버, 가리킴 말풍선(#hud-tip) ----------
  let helpAnchor = null;
  function closeHelp(restoreFocus) {
    const pop = $('#help-pop');
    if (!pop || pop.hidden) return false;
    pop.hidden = true;
    pop.classList.remove('is-leg');
    pop.innerHTML = '';
    const prev = helpAnchor;
    helpAnchor = null;
    if (prev) {
      prev.setAttribute('aria-expanded', 'false');
      if (restoreFocus) { try { prev.focus(); } catch (e) { /* */ } }
    }
    return true;
  }
  function positionPop(pop, anchor) {
    const r = anchor.getBoundingClientRect();
    const pw = pop.offsetWidth || 340, ph = pop.offsetHeight || 120;
    const left = Math.max(12, Math.min(innerWidth - pw - 12, Math.round(r.left - 8)));
    const below = r.bottom + 8 + ph <= innerHeight - 12;
    const top = below ? Math.round(r.bottom + 8) : Math.max(12, Math.round(r.top - ph - 8));
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';
  }
  function toggleHelp(btnEl) {
    const item = TERMS[btnEl.dataset.help];
    if (!item) return;
    const pop = $('#help-pop');
    if (!pop) return;
    if (helpAnchor === btnEl && !pop.hidden) { closeHelp(false); return; }
    closeHelp(false);
    helpAnchor = btnEl;
    btnEl.setAttribute('aria-expanded', 'true');
    pop.classList.remove('is-leg', 'is-peer');
    pop.innerHTML = `<div class="help-h"><span>${esc(cp(item.titleKey))}</span><button type="button" class="help-x" data-help-close="1" aria-label="${esc(cp('legendCloseAria'))}"><svg width="11" height="11" viewBox="0 0 14 14" aria-hidden="true"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8"/></svg></button></div><p class="help-p">${esc(cp(item.bodyKey))}</p>`;
    pop.hidden = false;
    positionPop(pop, btnEl);
  }
  function toggleLegend(btnEl) {
    const spec = LEGENDS[btnEl.dataset.legend] || LEGENDS.verdict;
    if (!spec) return;
    const pop = $('#help-pop');
    if (!pop) return;
    if (helpAnchor === btnEl && !pop.hidden) { closeHelp(false); return; }
    closeHelp(false);
    helpAnchor = btnEl;
    btnEl.setAttribute('aria-expanded', 'true');
    pop.classList.remove('is-peer');
    pop.classList.add('is-leg');
    pop.innerHTML = `<div class="help-h"><span>${esc(cp(spec.titleKey))}</span><button type="button" class="help-x" data-help-close="1" aria-label="${esc(cp('legendCloseAria'))}"><svg width="11" height="11" viewBox="0 0 14 14" aria-hidden="true"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8"/></svg></button></div>${spec.htmlFn(ctx())}`;
    pop.hidden = false;
    positionPop(pop, btnEl);
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
        ${groups.map(g => `<div class="peer-grp"><div class="peer-gh">${esc(g.t)}</div><div class="peer-gl">${g.list.map(code => {
          const on = st.peerScope === 'custom' ? picked.has(code) : activePeerOrgs().includes(code);
          return `<button type="button" class="peer-chk${on ? ' is-on' : ''}" data-peer-org="${esc(code)}" aria-pressed="${on}"><i></i><span>${esc(orgShort(code))}</span></button>`;
        }).join('')}</div></div>`).join('')}
      </div>`;
  }
  function togglePeerPop(btnEl) {
    const pop = $('#help-pop');
    if (!pop) return;
    if (helpAnchor === btnEl && !pop.hidden) { closeHelp(false); return; }
    closeHelp(false);
    helpAnchor = btnEl;
    btnEl.setAttribute('aria-expanded', 'true');
    pop.classList.remove('is-leg');
    pop.classList.add('is-peer');
    pop.innerHTML = renderPeerPopBody();
    pop.hidden = false;
    positionPop(pop, btnEl);
  }

  let tipAnchor = null, touchTimer = 0;
  function showHudTip(el) {
    const tip = $('#hud-tip');
    const text = el && el.dataset && el.dataset.tip;
    if (!tip || !text) return;
    const r = el.getBoundingClientRect();
    const headEl = $('#head');
    const minTop = (headEl ? Math.max(0, headEl.getBoundingClientRect().bottom) : 66) + 6;
    if (r.width < 1 || r.bottom <= minTop || r.top >= innerHeight) { hideHudTip(); return; }
    tipAnchor = el;
    tip.textContent = text;
    tip.hidden = false;
    const tw = tip.offsetWidth || 220, th = tip.offsetHeight || 36;
    const left = Math.max(10, Math.min(innerWidth - tw - 10, Math.round(r.left + r.width / 2 - tw / 2)));
    const top = r.top - th - 8 >= minTop ? Math.round(r.top - th - 8) : Math.min(innerHeight - th - 8, Math.max(minTop, Math.round(r.bottom + 8)));
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function hideHudTip() {
    clearTimeout(touchTimer);
    tipAnchor = null;
    const tip = $('#hud-tip');
    if (tip) tip.hidden = true;
  }
  document.addEventListener('pointerover', e => {
    if (e.pointerType === 'touch') return;
    const el = e.target.closest && e.target.closest('[data-tip]');
    if (el) showHudTip(el); else if (tipAnchor) hideHudTip();
  });
  document.addEventListener('pointerout', e => {
    if (tipAnchor && (!e.relatedTarget || !tipAnchor.contains(e.relatedTarget))) hideHudTip();
  });
  document.addEventListener('focusin', e => {
    if (e.target.matches && !e.target.matches(':focus-visible')) return;
    const el = e.target.closest && e.target.closest('[data-tip]');
    if (el) showHudTip(el);
  });
  document.addEventListener('focusout', () => hideHudTip());
  document.addEventListener('touchstart', e => {
    const el = e.target.closest && e.target.closest('[data-tip]');
    clearTimeout(touchTimer);
    if (el) touchTimer = setTimeout(() => showHudTip(el), 320);
  }, { passive: true });
  document.addEventListener('touchmove', () => clearTimeout(touchTimer), { passive: true });
  document.addEventListener('touchend', () => clearTimeout(touchTimer), { passive: true });

  addEventListener('scroll', () => { closeHelp(false); hideHudTip(); }, { passive: true });
  on('tab', () => { closeHelp(false); hideHudTip(); });
  on('change', (_, opts) => { if (!opts || !opts.keepPop) closeHelp(false); hideHudTip(); });

  // ---------- 위임한 눌림과 키보드 ----------
  document.addEventListener('click', e => {
    hideHudTip();
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
      if (pop && !pop.hidden) pop.innerHTML = renderPeerPopBody();
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
    const hb = e.target.closest('[data-help]');
    if (hb) { e.stopPropagation(); toggleHelp(hb); return; }
    const lb = e.target.closest('[data-legend]');
    if (lb) { e.stopPropagation(); toggleLegend(lb); return; }
    if (!e.target.closest('#help-pop')) closeHelp(false);

    const lt = e.target.closest('[data-layer-to]');
    if (lt) {
      e.stopPropagation();
      const lv = +lt.dataset.layerTo;
      if (lv <= 1) unselect();
      else if (lv === 2) selectSub(null);
      return;
    }
    const lu = e.target.closest('[data-layer-up]');
    if (lu) { e.stopPropagation(); stepUp(); return; }
    const ts = e.target.closest('[data-tab-step]');
    if (ts) {
      e.stopPropagation();
      const d = +ts.dataset.tabStep || 1;
      const i = TAB_IDS.indexOf(st.tab);
      set({ tab: TAB_IDS[(i + d + TAB_IDS.length) % TAB_IDS.length] });
      return;
    }

    const a = e.target.closest('[data-act],[data-go],button[data-copy],button[data-print]');
    if (a) {
      if (a.dataset.go) { e.stopPropagation(); go(a.dataset.go, { focus: a.dataset.focus }); return; }
      if (a.dataset.copy) { e.stopPropagation(); copyTable(a.dataset.copy, { title: a.dataset.title }); return; }
      if (a.dataset.print) { e.stopPropagation(); print(a.dataset.print, { title: a.dataset.title, card: a.dataset.card === '1' }); return; }
      if (a.dataset.act === 'base-to') { set({ base: a.dataset.v }); return; }
      if (a.dataset.act) return;
    }
    const sp = e.target.closest('.view [data-sub-pick]');
    if (sp && !e.target.closest('.live')) { selectSub(sp.dataset.subPick); return; }
    const p = e.target.closest('.view [data-pick]');
    if (p && !e.target.closest('.live')) select(p.dataset.pick);
  });

  document.addEventListener('keydown', e => {
    const p = e.target.closest && e.target.closest('.view tr[data-pick]');
    if (p && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); select(p.dataset.pick); return; }
    if (e.key === 'Escape') {
      if (stepUp()) { e.preventDefault(); return; }
    }
    const typing = e.target.closest && e.target.closest('input,select,textarea');
    if (typing) return;
    if (e.key === ']' || e.key === '[') {
      const i = TAB_IDS.indexOf(st.tab);
      set({ tab: TAB_IDS[(i + (e.key === ']' ? 1 : TAB_IDS.length - 1)) % TAB_IDS.length] });
    }
  });

  // ---------- 탭 등록 ----------
  function registerTab(def) {
    if (!def || !TAB_IDS.includes(def.id)) throw new Error('Unknown tab: ' + (def && def.id));
    tabs[def.id] = Object.assign({ kicker: '' }, def, { _dirty: true, _drawn: false });
    if (booted) {
      const sec = viewOf(def.id);
      if (sec) $('.ttl', sec).outerHTML = title(def.id, def.kicker, TAB_NAME[def.id]);
      if (def.id === st.tab) showTab(st.tab);
    }
  }

  // ---------- 시작 ----------
  function boot() {
    const saved = { skin: store.get(LS_SKIN), motion: store.get(LS_MOTION) };
    if (saved.skin === 'dark' || saved.skin === 'light') st.skin = saved.skin;
    if (saved.motion === 'on' || saved.motion === 'off') st.motion = saved.motion;
    else if (matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) st.motion = 'off';
    const initHash = decodeHash(location.hash);
    Object.assign(st, initHash.patch);
    if (initHash.pick != null) st.sel[st.tab] = initHash.pick;
    if (initHash.sub != null && initHash.pick != null) st.sub[st.tab] = initHash.sub;
    if (st.since == null) st.surg = false;
    applySkin(); applyMotion();

    // tpl.html 의 고정 문구도 COPY 표에서 동기화
    if ($('#app-title')) $('#app-title').textContent = cp('appTitle');
    if ($('#boot-loader')) $('#boot-loader').setAttribute('aria-label', cp('bootAria'));
    if ($('#condmini')) $('#condmini').title = cp('condMiniTitle');
    if ($('#ev')) $('#ev').setAttribute('aria-label', cp('evAria'));
    if ($('#ev-pnm-t')) $('#ev-pnm-t').textContent = cp('evPanelName');
    if ($('#ev-x')) $('#ev-x').setAttribute('aria-label', cp('evCloseAria'));
    if ($('#foot-notice-h')) $('#foot-notice-h').textContent = cp('footNoticeHead');
    if ($('#foot-disclaimer')) $('#foot-disclaimer').textContent = cp('footDisclaimer');
    if ($('#asof-label')) $('#asof-label').textContent = cp('footAsof');
    if ($('#foot-font-h')) $('#foot-font-h').textContent = cp('footFontHead');
    $('#asof').textContent = asofText();
    $('#notice-t').textContent = S['고지'];
    $('#foot-notice').textContent = S['고지'];
    const eh = $('#ev-help');
    if (eh) eh.outerHTML = help('ev-panel', cp('evPanelName'));

    renderCond(); renderScope(); renderTabs();
    $('#skin').addEventListener('click', () => set({ skin: st.skin === 'dark' ? 'light' : 'dark' }));
    $('#motion').addEventListener('click', () => set({ motion: st.motion === 'on' ? 'off' : 'on' }));
    $('#ev-x').addEventListener('click', () => stepUp());
    $('#condmini').addEventListener('click', () => { scrollTo({ top: 0, behavior: motionOn() ? 'smooth' : 'auto' }); });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(es => { for (const x of es) $('#head').classList.toggle('cond-away', !x.isIntersecting); }, { rootMargin: '-80px 0px 0px 0px' }).observe($('#cond'));
    }
    let rz = 0, lastMode = mode();
    addEventListener('resize', () => {
      clearTimeout(rz);
      rz = setTimeout(() => {
        const m = mode();
        if (m !== lastMode) { if (m === 'wide') { EV.open = false; document.body.classList.remove('ev-open'); } lastMode = m; }
        closeHelp(false); hideHudTip();
        sheetPad(); placeEv(); placeGuides(); fitSel(); emit('resize', m);
      }, 80);
    });
    $('#work').addEventListener('transitionend', e => { if (e.target === $('#work')) { placeGuides(); fitSel(); } });
    booted = true;
    try { history.replaceState({ c4: 1 }, '', encodeHash()); } catch (e) { /* */ }
    showTab(st.tab, { scroll: false });
    placeEv(); setTimeout(() => { placeEv(); placeGuides(); }, 50);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { placeGuides(); fitSel(); });
  }

  window.App = {
    S, D: DD, COPY, t: cp, TAB_IDS, TAB_NAME, TAB_BY_NAME, ORG_ORDER, PEER_ORGS, REF,
    get state() { return { ...st, peerPick: st.peerPick.slice(), sel: { ...st.sel }, sub: { ...st.sub } }; },
    set, on, ctx: () => ctx(), registerTab, go, select, selectSub, unselect, stepUp, syncPath, reveal,
    ev: { show: showEv, open: openEv, close: () => unselect(), def: () => showDefaultEv(true), legend: legendHTML },
    ui: UI, txt: TXT, mode, motionOn,
    cellOf, segPatch, segPatchText, samePatch, activePeerOrgs, activeOrgs, orgSector,
    limitOf, mapOf, condSummary, condSegOnly, scopeLine, asofText,
    copyText, copyRows, copyTable, print, toast, fitSel,
    boot,
  };
})();
