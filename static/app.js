const state = {
  board: [],
  pieceNames: {},
  currentPlayer: "r",
  winner: null,
  selected: null,
  validMoves: [],
  busy: false,
  level: "medium",
  mode: "free",
  courses: [],
  activeCourseId: null,
  activeSectionIndex: 0,
  sectionCount: 0,
  sectionType: null,
  boardMetrics: {
    marginX: 70,
    marginY: 70,
    stepX: 60,
    stepY: 68,
  },
};

const SVG_NS = "http://www.w3.org/2000/svg";
const boardSvg = document.getElementById("board-svg");
const statusText = document.getElementById("status-text");
const levelSelect = document.getElementById("level-select");
const modeSelect = document.getElementById("mode-select");
const courseControls = document.getElementById("course-controls");
const courseSelect = document.getElementById("course-select");
const nextSectionBtn = document.getElementById("next-section-btn");
const stopCourseBtn = document.getElementById("stop-course-btn");
const resetBtn = document.getElementById("reset-btn");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const quickAskBtn = document.getElementById("quick-ask-btn");
const clearChatBtn = document.getElementById("clear-chat-btn");
let pieceGroupLayer = null;
let hintGroupLayer = null;

function boardPoint(row, col) {
  return {
    x: state.boardMetrics.marginX + col * state.boardMetrics.stepX,
    y: state.boardMetrics.marginY + row * state.boardMetrics.stepY,
  };
}

function drawBoardSvg() {
  const { marginX, marginY, stepX, stepY } = state.boardMetrics;
  const right = marginX + stepX * 8;
  const bottom = marginY + stepY * 9;
  const files = ["a", "b", "c", "d", "e", "f", "g", "h", "i"];
  const ranks = ["9", "8", "7", "6", "5", "4", "3", "2", "1", "0"];

  const lines = [];
  for (let col = 0; col < 9; col += 1) {
    const x = marginX + stepX * col;
    if (col === 0 || col === 8) {
      lines.push(`<line x1="${x}" y1="${marginY}" x2="${x}" y2="${bottom}" />`);
    } else {
      lines.push(`<line x1="${x}" y1="${marginY}" x2="${x}" y2="${marginY + stepY * 4}" />`);
      lines.push(`<line x1="${x}" y1="${marginY + stepY * 5}" x2="${x}" y2="${bottom}" />`);
    }
  }
  for (let row = 0; row < 10; row += 1) {
    const y = marginY + stepY * row;
    lines.push(`<line x1="${marginX}" y1="${y}" x2="${right}" y2="${y}" />`);
  }

  lines.push(`<line x1="${marginX + stepX * 3}" y1="${marginY}" x2="${marginX + stepX * 5}" y2="${marginY + stepY * 2}" />`);
  lines.push(`<line x1="${marginX + stepX * 5}" y1="${marginY}" x2="${marginX + stepX * 3}" y2="${marginY + stepY * 2}" />`);
  lines.push(`<line x1="${marginX + stepX * 3}" y1="${marginY + stepY * 7}" x2="${marginX + stepX * 5}" y2="${marginY + stepY * 9}" />`);
  lines.push(`<line x1="${marginX + stepX * 5}" y1="${marginY + stepY * 7}" x2="${marginX + stepX * 3}" y2="${marginY + stepY * 9}" />`);

  const fileLabels = files.map((file, index) => {
    const x = marginX + stepX * index;
    return `<text x="${x}" y="${marginY - 38}" text-anchor="middle" fill="#8d5b2a" font-size="18" font-weight="700">${file}</text>
    <text x="${x}" y="${bottom + 46}" text-anchor="middle" fill="#8d5b2a" font-size="18" font-weight="700">${file}</text>`;
  }).join("");
  const rankLabels = ranks.map((rank, index) => {
    const y = marginY + stepY * index + 6;
    return `<text x="${marginX - 42}" y="${y}" text-anchor="middle" fill="#8d5b2a" font-size="18" font-weight="700">${rank}</text>
    <text x="${right + 42}" y="${y}" text-anchor="middle" fill="#8d5b2a" font-size="18" font-weight="700">${rank}</text>`;
  }).join("");

  boardSvg.innerHTML = `
    <g stroke="#6e4a22" stroke-width="3" fill="none" stroke-linecap="round">
      ${lines.join("")}
    </g>
    ${fileLabels}
    ${rankLabels}
    <text x="${marginX + stepX * 1.5}" y="${marginY + stepY * 4.6}" text-anchor="middle" fill="#8d5b2a" font-size="34" font-weight="700">楚河</text>
    <text x="${marginX + stepX * 5.5}" y="${marginY + stepY * 4.6}" text-anchor="middle" fill="#8d5b2a" font-size="34" font-weight="700">汉界</text>
    <g id="hint-group"></g>
    <g id="piece-group"></g>
  `;
  hintGroupLayer = document.getElementById("hint-group");
  pieceGroupLayer = document.getElementById("piece-group");
}

function renderBoard() {
  if (!pieceGroupLayer || !hintGroupLayer) {
    drawBoardSvg();
  }
  pieceGroupLayer.innerHTML = "";
  hintGroupLayer.innerHTML = "";
  statusText.textContent = currentStatusText();

  state.board.forEach((rowData, row) => {
    rowData.forEach((piece, col) => {
      if (!piece) return;
      const point = boardPoint(row, col);
      const currentSide = state.currentPlayer;
      const isSelectable = piece.startsWith(currentSide) && !state.busy;
      const isSelected = Boolean(state.selected && state.selected.row === row && state.selected.col === col);
      const pieceNode = createPieceNode(point.x, point.y, state.pieceNames[piece], piece, isSelectable, isSelected);
      pieceNode.addEventListener("click", () => onPieceClick(row, col, piece));
      pieceGroupLayer.appendChild(pieceNode);
    });
  });

  state.validMoves.forEach((move) => {
    const point = boardPoint(move.row, move.col);
    const targetPiece = state.board[move.row][move.col];
    const hint = createHintNode(point.x, point.y, Boolean(targetPiece));
    hint.addEventListener("click", () => onHintClick(move.row, move.col));
    hintGroupLayer.appendChild(hint);
  });
}

function createSvgNode(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  Object.entries(attrs).forEach(([key, value]) => {
    node.setAttribute(key, value);
  });
  return node;
}

function createPieceNode(x, y, text, piece, selectable, selected) {
  const group = createSvgNode("g", { class: `piece-group${selectable ? " selectable" : ""}` });
  const circle = createSvgNode("circle", {
    cx: x,
    cy: y,
    r: 30,
    class: `piece-circle${selected ? " piece-selected" : ""}`,
  });
  const label = createSvgNode("text", {
    x,
    y: y + 1,
    class: `piece-text ${piece.startsWith("r") ? "red" : "black"}`,
  });
  label.textContent = text;
  group.appendChild(circle);
  group.appendChild(label);
  return group;
}

function createHintNode(x, y, capture) {
  return createSvgNode("circle", {
    cx: x,
    cy: y,
    r: capture ? 32 : 9,
    class: capture ? "hint-capture" : "hint-move",
  });
}

function currentStatusText() {
  if (state.winner === "r") return "对局结束，红方获胜。";
  if (state.winner === "b") return "对局结束，黑方获胜。";
  if (state.mode === "course" && state.activeCourseId) {
    return `课程模式：第 ${state.activeSectionIndex + 1}/${state.sectionCount} 节`;
  }
  return state.currentPlayer === "r" ? "轮到红方行棋。" : "轮到黑方行棋。";
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const rawText = await response.text();
  let data = null;

  if (rawText) {
    try {
      data = JSON.parse(rawText);
    } catch (error) {
      throw new Error(`服务器返回了无效响应（${response.status}）`);
    }
  }

  if (!response.ok) {
    const message = data?.error || data?.message || `请求失败（${response.status}）`;
    throw new Error(message);
  }

  return data;
}

function applyCourseState(courseState) {
  const active = Boolean(courseState?.active);
  state.mode = active ? "course" : "free";
  state.activeCourseId = active ? courseState.course_id : null;
  state.activeSectionIndex = active ? courseState.section_index : 0;
  state.sectionCount = active ? courseState.section_count : 0;
  state.sectionType = active ? courseState.section_type : null;
  modeSelect.value = state.mode;
  courseControls.classList.toggle("hidden", !active);
  courseSelect.value = active ? courseState.course_id : (state.courses[0]?.id || "");
}

function applyState(data) {
  state.board = data.board;
  state.pieceNames = data.piece_names;
  state.currentPlayer = data.current_player;
  state.winner = data.winner;
  state.level = data.level;
  state.selected = null;
  state.validMoves = [];
  levelSelect.value = data.level;
  applyCourseState(data.course_state);
  renderBoard();
}

function maybeAnnounceWinner(stateData) {
  if (!stateData?.winner) return;
  if (state.mode === "course") {
    addMessage("assistant", stateData.winner === "r" ? "这一节已经走成将死，红方获胜。" : "这一节已经结束，黑方获胜。");
    return;
  }
  addMessage("assistant", stateData.winner === "r" ? "本局结束，红方获胜。" : "本局结束，黑方获胜。");
}

function cloneBoard(board) {
  return board.map((row) => [...row]);
}

function applyEventToBoard(board, event) {
  const nextBoard = cloneBoard(board);
  nextBoard[event.from[0]][event.from[1]] = null;
  nextBoard[event.to[0]][event.to[1]] = event.piece;
  return nextBoard;
}

function fillCourseSelect(courses) {
  courseSelect.innerHTML = "";
  courses.forEach((course) => {
    const option = document.createElement("option");
    option.value = course.id;
    option.textContent = course.title;
    courseSelect.appendChild(option);
  });
}

async function loadCourses() {
  const data = await fetchJson("/api/courses");
  state.courses = data.courses || [];
  fillCourseSelect(state.courses);
}

async function loadState() {
  const data = await fetchJson("/api/state");
  applyState(data);
}

async function loadCourseState() {
  const data = await fetchJson("/api/course/state");
  applyCourseState(data);
}

function addMessage(role, text, extraClass = "") {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;
  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${extraClass}`.trim();
  bubble.dataset.rawText = String(text || "");
  bubble.textContent = role === "assistant" ? formatAssistantMessage(text) : text;
  row.appendChild(bubble);
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return bubble;
}

function setAssistantBubbleText(bubble, text) {
  bubble.dataset.rawText = String(text || "");
  bubble.textContent = formatAssistantMessage(text);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendAssistantBubbleText(bubble, chunk) {
  const nextText = `${bubble.dataset.rawText || ""}${chunk || ""}`;
  setAssistantBubbleText(bubble, nextText);
}

function decorateFallbackMessage(text, source) {
  if (source === "fallback") {
    return `本轮为本地兜底讲解，不是完整 LLM 回复。\n\n${text}`;
  }
  return text;
}

function formatAssistantMessage(text) {
  return String(text || "")
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/^-\s+/gm, "• ")
    .replace(/`/g, "")
    .trim();
}

function appendSectionMessage(courseState) {
  if (!courseState?.active || !courseState.section_content) return;
  const header = `${courseState.course_title}\n${courseState.section_title}`;
  const hintText = (courseState.section_hints || []).length
    ? `\n\n提示：\n${courseState.section_hints.map((hint) => `- ${hint}`).join("\n")}`
    : "";
  addMessage("assistant", `${header}\n\n${courseState.section_content}${hintText}`);
}

async function startLesson(courseId) {
  const data = await fetchJson("/api/course/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ course_id: courseId, lesson_index: 0 }),
  });
  applyState(data.state);
  appendSectionMessage(data.course_state);
}

async function fetchEventStream(url, options, handlers) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `请求失败（${response.status}）`);
  }
  if (!response.body) {
    throw new Error("浏览器不支持流式响应。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      handleSseEvent(rawEvent, handlers);
      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      if (buffer.trim()) {
        handleSseEvent(buffer, handlers);
      }
      break;
    }
  }
}

function handleSseEvent(rawEvent, handlers) {
  if (!rawEvent.trim()) return;

  let eventName = "message";
  const dataLines = [];
  rawEvent.split("\n").forEach((line) => {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  });

  const payloadText = dataLines.join("\n");
  let payload = {};
  if (payloadText) {
    try {
      payload = JSON.parse(payloadText);
    } catch (error) {
      payload = { text: payloadText };
    }
  }

  const handler = handlers[eventName];
  if (handler) {
    handler(payload);
  }
}

async function sendCourseMessage(message) {
  const typingBubble = addMessage("assistant", "正在结合当前课程与棋盘分析…", "typing");
  try {
    let finalData = null;
    setAssistantBubbleText(typingBubble, "");
    await fetchEventStream("/api/course/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    }, {
      chunk: (payload) => appendAssistantBubbleText(typingBubble, payload.text || ""),
      replace: (payload) => setAssistantBubbleText(typingBubble, payload.text || ""),
      done: (payload) => {
        finalData = payload;
      },
    });
    const finalText = decorateFallbackMessage(finalData?.message || finalData?.error || "没有收到回复。", finalData?.source);
    setAssistantBubbleText(typingBubble, finalText);
    typingBubble.classList.remove("typing");
  } catch (error) {
    setAssistantBubbleText(typingBubble, `调用失败：${error.message}`);
    typingBubble.classList.remove("typing");
  }
}

async function nextSection() {
  try {
    const data = await fetchJson("/api/course/next-section", { method: "POST" });
    applyState(data.state);
    appendSectionMessage(data.course_state);
  } catch (error) {
    addMessage("assistant", `切换下一节失败：${error.message}`);
  }
}

async function exitCourse() {
  try {
    const data = await fetchJson("/api/course/stop", { method: "POST" });
    applyState(data.state);
    addMessage("assistant", "已退出课程模式，回到自由对弈。");
  } catch (error) {
    addMessage("assistant", `退出课程失败：${error.message}`);
  }
}

async function onPieceClick(row, col, piece) {
  if (state.busy || state.winner) return;

  if (state.selected) {
    const selectedMove = state.validMoves.find((move) => move.row === row && move.col === col);
    if (selectedMove) {
      await onHintClick(row, col);
      return;
    }
  }

  if (!piece.startsWith(state.currentPlayer)) return;

  if (state.selected && state.selected.row === row && state.selected.col === col) {
    state.selected = null;
    state.validMoves = [];
    renderBoard();
    return;
  }

  try {
    const data = await fetchJson(`/api/legal-moves?row=${row}&col=${col}`);
    state.selected = { row, col };
    state.validMoves = data.moves;
    renderBoard();
  } catch (error) {
    addMessage("assistant", `读取可走步失败：${error.message}`);
  }
}

async function onHintClick(toRow, toCol) {
  if (!state.selected || state.busy) return;
  state.busy = true;
  const payload = {
    from_row: state.selected.row,
    from_col: state.selected.col,
    to_row: toRow,
    to_col: toCol,
  };

  try {
    const data = await fetchJson("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await animateEvents(data.events, data.state);
    maybeAnnounceWinner(data.state);
  } catch (error) {
    addMessage("assistant", `走子失败：${error.message}`);
    await loadState();
  } finally {
    state.busy = false;
  }
}

async function animateEvents(events, finalState) {
  let animatedBoard = cloneBoard(state.board);
  for (const event of events) {
    animatedBoard = await animateSingleEvent(event, animatedBoard);
  }
  applyState(finalState);
}

function animateSingleEvent(event, boardBeforeMove) {
  return new Promise((resolve) => {
    const fromPoint = boardPoint(event.from[0], event.from[1]);
    const toPoint = boardPoint(event.to[0], event.to[1]);
    const boardAfterMove = applyEventToBoard(boardBeforeMove, event);

    state.board = boardBeforeMove;
    state.board[event.from[0]][event.from[1]] = null;
    state.board[event.to[0]][event.to[1]] = null;
    state.selected = null;
    state.validMoves = [];
    renderBoard();

    const overlay = createPieceNode(
      fromPoint.x,
      fromPoint.y,
      state.pieceNames[event.piece],
      event.piece,
      false,
      false,
    );
    const overlayCircle = overlay.querySelector("circle");
    const overlayText = overlay.querySelector("text");
    pieceGroupLayer.appendChild(overlay);
    const startTime = performance.now();
    const duration = 240;

    function step(now) {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - (1 - progress) * (1 - progress);
      const cx = fromPoint.x + (toPoint.x - fromPoint.x) * eased;
      const cy = fromPoint.y + (toPoint.y - fromPoint.y) * eased;
      overlayCircle.setAttribute("cx", cx);
      overlayCircle.setAttribute("cy", cy);
      overlayText.setAttribute("x", cx);
      overlayText.setAttribute("y", cy + 1);
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        overlay.remove();
        state.board = boardAfterMove;
        renderBoard();
        resolve(boardAfterMove);
      }
    }

    requestAnimationFrame(step);
  });
}

async function sendMessage() {
  const message = chatInput.value.trim();
  if (!message || state.busy) return;
  chatInput.value = "";
  await sendUserMessage(message);
}

async function sendUserMessage(message) {
  if (!message || state.busy) return;
  addMessage("user", message);
  sendBtn.disabled = true;
  quickAskBtn.disabled = true;
  try {
    if (state.mode === "course") {
      await sendCourseMessage(message);
      return;
    }

    const typingBubble = addMessage("assistant", "正在读取当前棋局，并请 Pikafish 与 Qwen 一起分析…", "typing");
    let finalData = null;
    setAssistantBubbleText(typingBubble, "");
    await fetchEventStream("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    }, {
      chunk: (payload) => appendAssistantBubbleText(typingBubble, payload.text || ""),
      done: (payload) => {
        finalData = payload;
      },
    });
    const finalText = decorateFallbackMessage(finalData?.message || finalData?.error || "没有收到回复。", finalData?.source);
    setAssistantBubbleText(typingBubble, finalText);
    typingBubble.classList.remove("typing");
  } catch (error) {
    addMessage("assistant", `调用失败：${error.message}`);
  } finally {
    sendBtn.disabled = false;
    quickAskBtn.disabled = false;
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
}

async function quickAsk() {
  const prompt = state.mode === "course" ? "请给我一个简短提示。" : "下一步怎么走比较好？";
  chatInput.value = "";
  await sendUserMessage(prompt);
}

function clearChat() {
  chatMessages.innerHTML = "";
}

async function resetGame() {
  if (state.busy) return;
  state.busy = true;
  try {
    const data = await fetchJson("/api/reset", { method: "POST" });
    applyState(data.state);
    addMessage("assistant", state.mode === "course" ? "当前课程节已重置。" : "棋局已经重新开始。");
  } catch (error) {
    addMessage("assistant", `重置失败：${error.message}`);
  } finally {
    state.busy = false;
  }
}

async function changeLevel() {
  try {
    const data = await fetchJson("/api/level", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: levelSelect.value }),
    });
    applyState(data.state);
    addMessage("assistant", `Pikafish 难度已切换为 ${levelSelect.options[levelSelect.selectedIndex].text}。`);
  } catch (error) {
    addMessage("assistant", `切换难度失败：${error.message}`);
  }
}

async function onModeChange() {
  if (modeSelect.value === "course") {
    const courseId = courseSelect.value || state.courses[0]?.id;
    if (!courseId) {
      addMessage("assistant", "当前没有可用课程。");
      modeSelect.value = "free";
      return;
    }
    try {
      await startLesson(courseId);
    } catch (error) {
      addMessage("assistant", `启动课程失败：${error.message}`);
      modeSelect.value = "free";
    }
    return;
  }

  await exitCourse();
}

drawBoardSvg();
levelSelect.addEventListener("change", changeLevel);
modeSelect.addEventListener("change", onModeChange);
courseSelect.addEventListener("change", async () => {
  if (state.mode === "course") {
    await startLesson(courseSelect.value);
  }
});
nextSectionBtn.addEventListener("click", nextSection);
stopCourseBtn.addEventListener("click", exitCourse);
resetBtn.addEventListener("click", resetGame);
sendBtn.addEventListener("click", sendMessage);
quickAskBtn.addEventListener("click", quickAsk);
clearChatBtn.addEventListener("click", clearChat);
chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

Promise.all([loadCourses(), loadState(), loadCourseState()])
  .then(() => {
    addMessage("assistant", "你好，我是你的象棋老师。你可以自由对弈，也可以切换到课程教学模式。");
  })
  .catch((error) => {
    addMessage("assistant", `初始化失败：${error.message}`);
  });
