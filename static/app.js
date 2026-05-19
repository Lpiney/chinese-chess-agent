const state = {
  board: [],
  pieceNames: {},
  currentPlayer: "r",
  winner: null,
  selected: null,
  validMoves: [],
  busy: false,
  level: "medium",
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
const resetBtn = document.getElementById("reset-btn");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
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

  boardSvg.innerHTML = `
    <g stroke="#6e4a22" stroke-width="3" fill="none" stroke-linecap="round">
      ${lines.join("")}
    </g>
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
      const isSelectable = state.currentPlayer === "r" && piece.startsWith("r") && !state.busy;
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

async function loadState() {
  try {
    const data = await fetchJson("/api/state");
    applyState(data);
  } catch (error) {
    statusText.textContent = `棋局加载失败：${error.message}`;
  }
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
  renderBoard();
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

async function onPieceClick(row, col, piece) {
  if (state.busy || state.winner || state.currentPlayer !== "r") return;

  if (state.selected) {
    const selectedMove = state.validMoves.find((move) => move.row === row && move.col === col);
    if (selectedMove) {
      await onHintClick(row, col);
      return;
    }
  }

  if (!piece.startsWith("r")) return;

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
    if (!data.ok) {
      addMessage("assistant", `走子失败：${data.error}`);
      state.busy = false;
      await loadState();
      return;
    }

    await animateEvents(data.events, data.state);
  } catch (error) {
    addMessage("assistant", `走子失败：${error.message}`);
    state.busy = false;
    await loadState();
    return;
  }
  state.busy = false;
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

function addMessage(role, text, extraClass = "") {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;
  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${extraClass}`.trim();
  bubble.textContent = role === "assistant" ? formatAssistantMessage(text) : text;
  row.appendChild(bubble);
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return bubble;
}

function formatAssistantMessage(text) {
  return text
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/^-\s+/gm, "• ")
    .replace(/`/g, "")
    .trim();
}

async function sendMessage() {
  const message = chatInput.value.trim();
  if (!message || state.busy) return;
  chatInput.value = "";
  addMessage("user", message);
  const typingBubble = addMessage("assistant", "正在读取当前棋局，并请 Pikafish 与 DeepSeek 一起分析…", "typing");

  sendBtn.disabled = true;
  try {
    const data = await fetchJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    typingBubble.textContent = formatAssistantMessage(data.message || data.error || "没有收到回复。");
    typingBubble.classList.remove("typing");
  } catch (error) {
    typingBubble.textContent = `调用失败：${error.message}`;
    typingBubble.classList.remove("typing");
  } finally {
    sendBtn.disabled = false;
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
}

async function resetGame() {
  if (state.busy) return;
  state.busy = true;
  try {
    const data = await fetchJson("/api/reset", { method: "POST" });
    applyState(data.state);
    addMessage("assistant", "棋局已经重新开始。你可以继续问我：现在第一步该怎么走？");
  } catch (error) {
    addMessage("assistant", `重置失败：${error.message}`);
  }
  state.busy = false;
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

drawBoardSvg();
levelSelect.addEventListener("change", changeLevel);
resetBtn.addEventListener("click", resetGame);
sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

loadState().then(() => {
  addMessage("assistant", "你好，我是你的象棋老师。你可以问我：下一步该怎么走、为什么这步最好、现在谁更好。");
});
