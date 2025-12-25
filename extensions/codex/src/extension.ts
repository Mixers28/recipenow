import * as vscode from "vscode";
import { basename } from "path";
import { WorkflowAgentResult, WorkflowOrchestrator } from "./orchestrator/WorkflowOrchestrator";

// Constants
const FRONTMATTER_DELIMITER = '---';
const INSTRUCTION_SEPARATOR = '\n\n---\n\n';

// Agent definitions
const AGENTS = [
  { label: "Architect", id: "mix.architect", description: "Design specs and acceptance criteria", icon: "symbol-class" },
  { label: "Coder", id: "mix.coder", description: "Implement requested changes", icon: "code" },
  { label: "Reviewer", id: "mix.reviewer", description: "Review for risks and test gaps", icon: "check" },
  { label: "QA", id: "mix.qa", description: "Produce focused test plans", icon: "beaker" }
] as const;

// TreeItem for handoff agents
class HandoffTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly participantId: string,
    public readonly description: string,
    public readonly iconId: string
  ) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.tooltip = description;
    this.contextValue = participantId.split('.')[1]; // e.g., "architect" from "mix.architect"
    this.iconPath = new vscode.ThemeIcon(iconId);
    this.command = {
      command: `codex.handoffTo${this.capitalizeFirst(this.contextValue)}`,
      title: `Hand off to ${label}`,
      arguments: [this]
    };
  }

  private capitalizeFirst(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
}

// TreeDataProvider for handoff view
class HandoffTreeProvider implements vscode.TreeDataProvider<HandoffTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<HandoffTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private handoffItems: HandoffTreeItem[] = AGENTS.map(
    agent => new HandoffTreeItem(agent.label, agent.id, agent.description, agent.icon)
  );

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: HandoffTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: HandoffTreeItem): Thenable<HandoffTreeItem[]> {
    if (element) {
      return Promise.resolve([]);
    }
    return Promise.resolve(this.handoffItems);
  }
}

export function activate(ctx: vscode.ExtensionContext) {
  // Register the TreeDataProvider
  const handoffProvider = new HandoffTreeProvider();
  const treeView = vscode.window.createTreeView('codexHandoffView', {
    treeDataProvider: handoffProvider,
    showCollapseAll: false
  });

  // Refresh command
  const refreshCommand = vscode.commands.registerCommand('codex.refreshHandoff', () => {
    handoffProvider.refresh();
  });

  // Handoff command handlers
  const handoffToArchitect = vscode.commands.registerCommand('codex.handoffToArchitect', async () => {
    await handoffToParticipant('mix.architect', 'Architect');
  });

  const handoffToCoder = vscode.commands.registerCommand('codex.handoffToCoder', async () => {
    await handoffToParticipant('mix.coder', 'Coder');
  });

  const handoffToReviewer = vscode.commands.registerCommand('codex.handoffToReviewer', async () => {
    await handoffToParticipant('mix.reviewer', 'Reviewer');
  });

  const handoffToQA = vscode.commands.registerCommand('codex.handoffToQA', async () => {
    await handoffToParticipant('mix.qa', 'QA');
  });

  const orchestrator = new WorkflowOrchestrator([...AGENTS], getAgentInstructions);

  // Helper function to read agent instructions from .agent.md files
  async function getAgentInstructions(participantName: string): Promise<string> {
    try {
      const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
      if (!workspaceFolder) {
        return "";
      }

      const agentFileName = `${participantName.toLowerCase()}.agent.md`;
      const agentFileUri = vscode.Uri.joinPath(workspaceFolder.uri, '.github', 'agents', agentFileName);

      try {
        const content = await vscode.workspace.fs.readFile(agentFileUri);
        // Convert Uint8Array to string using Buffer for better performance
        const contentStr = Buffer.from(content).toString('utf8');
        
        // Extract the content after the frontmatter (after the second ---)
        const parts = contentStr.split(FRONTMATTER_DELIMITER);
        if (parts.length >= 3) {
          // Return the markdown content after frontmatter
          return parts.slice(2).join(FRONTMATTER_DELIMITER).trim();
        }
        
        return contentStr;
      } catch (readError) {
        // File doesn't exist or can't be read
        console.warn(`[Codex] Agent file not found or unreadable: ${agentFileName}`);
        return "";
      }
    } catch (error) {
      // Unexpected error
      console.error(`[Codex] Failed to read agent instructions: ${error}`);
      return "";
    }
  }

  // Helper function to send chat request to participant
  async function handoffToParticipant(participantId: string, participantName: string, overridePrompt?: string) {
    let instruction = overridePrompt;

    // If no override, use selected text as context
    if (!instruction) {
      const editor = vscode.window.activeTextEditor;
      const MAX_CONTEXT_LENGTH = 200;
      
      // Get selected text if available
      if (editor && editor.selection && !editor.selection.isEmpty) {
        let context = editor.document.getText(editor.selection);
        // Truncate if too large
        instruction = context.length > MAX_CONTEXT_LENGTH 
          ? context.substring(0, MAX_CONTEXT_LENGTH)
          : context;
      }
    }

    // Get agent instructions from .agent.md file
    const agentInstructions = await getAgentInstructions(participantName);

    // Build the complete chat message with agent instructions prepended
    let chatMessage = `@${participantId}`;
    
    if (agentInstructions) {
      chatMessage += `${INSTRUCTION_SEPARATOR}${agentInstructions}${INSTRUCTION_SEPARATOR}`;
    }
    
    // Add context/instruction if available
    if (instruction) {
      chatMessage += instruction;
    }
    
    try {
      // Use the command to open chat panel with the message
      await vscode.commands.executeCommand('workbench.action.chat.open', {
        query: chatMessage
      });
    } catch (error) {
      vscode.window.showErrorMessage(`Failed to hand off to ${participantName}: ${error}`);
    }
  }
  // Codex (coordinator)
  const codex = vscode.chat.createChatParticipant("mix.codex", async (req, _chatCtx, stream, _token) => {
    stream.markdown(`Starting orchestrated workflow...\n`);

    const workflowResults = await orchestrator.runWorkflow(req.prompt);

    workflowResults.forEach(result => {
      stream.markdown(formatAgentSection(result));
    });

    if (workflowResults.length > 0) {
      stream.markdown(formatWorkflowSummary(workflowResults));
    }

    return { metadata: { workflowResults, basePrompt: req.prompt } };
  });

  codex.followupProvider = {
    provideFollowups(result, _context, _token) {
      const workflowResults = (result as any).metadata?.workflowResults as WorkflowAgentResult[] | undefined;
      const base = (result as any).metadata?.basePrompt ?? "";

      if (workflowResults?.length) {
        return workflowResults.map(r => ({
          label: `Run ${r.label}`,
          participant: r.agentId,
          prompt: r.prompt
        })) satisfies vscode.ChatFollowup[];
      }

      if (!base) return [];

      return [
        { label: "Hand off → Architect", participant: "mix.architect", prompt: base },
        { label: "Hand off → Coder", participant: "mix.coder", prompt: base },
        { label: "Hand off → Reviewer", participant: "mix.reviewer", prompt: base },
        { label: "Hand off → QA", participant: "mix.qa", prompt: base }
      ] satisfies vscode.ChatFollowup[];
    }
  };

  const architect = createParticipant("mix.architect", "Architect", getAgentInstructions);
  const coder = createParticipant("mix.coder", "Coder", getAgentInstructions);
  const reviewer = createParticipant("mix.reviewer", "Reviewer", getAgentInstructions);
  const qa = createParticipant("mix.qa", "QA", getAgentInstructions);

  const runFullWorkflowCommand = vscode.commands.registerCommand("codex.runFullWorkflow", async () => {
    const task = await vscode.window.showInputBox({
      prompt: "Enter task for full workflow",
      placeHolder: "What should the agents work on?"
    });

    if (!task || !task.trim()) return;

    // Run orchestrator (builds prompts for all agents)
    const results = await orchestrator.runWorkflow(task.trim());

    // Build combined prompt from all results
    const combinedPrompt = results.map(r => `${r.label}:\n${r.prompt}`).join("\n\n---\n\n");

    // Hand off to Coder with combined prompt
    await handoffToParticipant('mix.coder', 'Coder', combinedPrompt);
  });

  const handoffCommand = vscode.commands.registerCommand("codex.handoff", async () => {
    const picks = AGENTS.map(agent => ({ label: agent.label, id: agent.id }));

    const pick = await vscode.window.showQuickPick(picks, { placeHolder: "Select a handoff target" });
    if (!pick) return;

    await handoffToParticipant(pick.id, pick.label);
  });

  ctx.subscriptions.push(
    treeView,
    refreshCommand,
    handoffToArchitect,
    handoffToCoder,
    handoffToReviewer,
    handoffToQA,
    codex, 
    architect, 
    coder, 
    reviewer, 
    qa, 
    handoffCommand,
    runFullWorkflowCommand
  );
}

function createParticipant(
  id: string, 
  label: string, 
  getInstructions: (participantName: string) => Promise<string>
) {
  return vscode.chat.createChatParticipant(id, async (req, _chatCtx, stream, _token) => {
    // Load agent instructions when invoked directly
    const instructions = await getInstructions(label);
    
    if (instructions) {
      stream.markdown(`${instructions}\n\n---\n\n`);
    }
    
    stream.markdown(`${label} received the request:\n\n${req.prompt}`);
    return { metadata: { basePrompt: req.prompt } };
  });
}

function formatAgentSection(result: WorkflowAgentResult): string {
  const lines = [
    `### ${result.label}`,
    `@${result.agentId}`,
    "",
    result.prompt
  ];

  return lines.join("\n");
}

function formatWorkflowSummary(results: WorkflowAgentResult[]): string {
  const summary = results.map(r => `- ${r.label}: handoff prompt prepared`).join("\n");
  return ["---", "Multi-agent workflow prepared", summary].join("\n");
}
