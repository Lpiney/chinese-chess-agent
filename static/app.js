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

const boardSvg = document.getElementById("board-svg");
const pieceLayer = document.getElementById("piece-layer");
const hintLayer = document.getElementById("hint-layer");
const statusText = document.getElementById("status-text");
const levelSelect = document.getElementById("level-select");
const resetBtn = document.getElementById("reset-btn");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");

function boardPoint(row, col) {
  return {
    x: state.boardMetrics.marginX + col * state.boardMetrics.stepX,
    y: state.boardMetrics.marginY + row * state.boardMetrics.stepY,
  };
}

function drawBoardSvg() {
  const { marginX, marginY, stepX, stepY } = state.boardMetrics;
  const width = 620;
  const height = 736;
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
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="100%">
      <g stroke="#6e4a22" stroke-width="3" fill="none" stroke-linecap="round">
        ${lines.join("")}
      </g>
      <text x="${marginX + stepX * 1.5}" y="${marginY + stepY * 4.6}" text-anchor="middle" fill="#8d5b2a" font-size="34" font-weight="700">楚河</text>
      <text x="${marginX + stepX * 5.5}" y="${marginY + stepY * 4.6}" text-anchor="middle" fill="#8d5b2a" font-size="34" font-weight="700">汉界</text>
    </svg>
  `;
}

function renderBoard() {
  pieceLayer.innerHTML = "";
  hintLayer.innerHTML = "";
  statusText.textContent = currentStatusText();

  state.board.forEach((rowData, row) => {
    rowData.forEach((piece, col) => {
      if (!piece) return;
      const point = boardPoint(row, col);
      const button = document.createElement("button");
      button.className = `piece ${piece.startsWith("r") ? "red" : "black"}`;
      if (state.currentPlayer === "r" && piece.startsWith("r") && !state.busy) {
        button.classList.add("selectable");
      }
      if (state.selected && state.selected.row === row && state.selected.col === col) {
        button.classList.add("selected");
      }
      button.style.left = `${point.x}px`;
      button.style.top = `${point.y}px`;
      button.textContent = state.pieceNames[piece];
      button.addEventListener("click", () => onPieceClick(row, col, piece));
      pieceLayer.appendChild(button);
    });
  });

  state.validMoves.forEach((move) => {
    const point = boardPoint(move.row, move.col);
    const targetPiece = state.board[move.row][move.col];
    const hint = document.createElement("button");
    hint.className = `hint ${targetPiece ? "capture" : "move"}`;
    hint.style.left = `${point.x}px`;
    hint.style.top = `${point.y}px`;
    hint.addEventListener("click", () => onHintClick(move.row, move.col));
    hintLayer.appendChild(hint);
  });
}

function currentStatusText() {
  if (state.winner === "r") return "对局结束，红方获胜。";
  if (state.winner === "b") return "对局结束，黑方获胜。";
  return state.currentPlayer === "r" ? "轮到红方行棋。" : "轮到黑方行棋。";
}

async function loadState() {
  const response = await fetch("/api/state");
  const data = await response.json();
  applyState(data);
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

async function onPieceClick(row, col, piece) {
  if (state.busy || state.winner || state.currentPlayer !== "r" || !piece.startsWith("r")) return;
  if (state.selected && state.selected.row === row && state.selected.col === col) {
    state.selected = null;
    state.validMoves = [];
    renderBoard();
    return;
  }
  const response = await fetch(`/api/legal-moves?row=${row}&col=${col}`);
  const data = await response.json();
  state.selected = { row, col };
  state.validMoves = data.moves;
  renderBoard();
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

  const response = await fetch("/api/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!data.ok) {
    addMessage("assistant", `走子失败：${data.error}`);
    state.busy = false;
    await loadState();
    return;
  }

  await animateEvents(data.events, data.state);
  state.busy = false;
}

async function animateEvents(events, finalState) {
  for (const event of events) {
    await animateSingleEvent(event);
  }
  applyState(finalState);
}

function animateSingleEvent(event) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = `piece ${event.piece.startsWith("r") ? "red" : "black"}`;
    overlay.textContent = state.pieceNames[event.piece];
    const fromPoint = boardPoint(event.from[0], event.from[1]);
    const toPoint = boardPoint(event.to[0], event.to[1]);
    overlay.style.left = `${fromPoint.x}px`;
    overlay.style.top = `${fromPoint.y}px`;
    overlay.style.transition = "left 240ms ease, top 240ms ease";
    pieceLayer.appendChild(overlay);

    requestAnimationFrame(() => {
      overlay.style.left = `${toPoint.x}px`;
      overlay.style.top = `${toPoint.y}px`;
    });

    setTimeout(() => {
      overlay.remove();
      resolve();
    }, 260);
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
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await response.json();
    typingBubble.textContent = formatAssistantMessage(data.message);
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
  const response = await fetch("/api/reset", { method: "POST" });
  const data = await response.json();
  applyState(data.state);
  addMessage("assistant", "棋局已经重新开始。你可以继续问我：现在第一步该怎么走？");
  state.busy = false;
}

async function changeLevel() {
  const response = await fetch("/api/level", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ level: levelSelect.value }),
  });
  const data = await response.json();
  applyState(data.state);
  addMessage("assistant", `Pikafish 难度已切换为 ${levelSelect.options[levelSelect.selectedIndex].text}。`);
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
