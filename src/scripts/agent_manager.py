import os
import threading
import time
from PySide6.QtCore import QThread



class AgentManager:
    """
    Centralized manager for all trading agents.
    
    Responsibilities:
    1. Track agent states (READY, RUNNING, STOPPING, STOPPED, ERROR)
    2. Create, start, stop, and restart agent threads
    3. Manage concurrent execution of multiple agents
    4. Handle cleanup and resource management
    5. Provide status information for the UI
    """
    STATE_INACTIVE = "Inactive"  # Not running, can be started
    STATE_ACTIVE = "Active"      # Currently running
    
    def __init__(self, src_path=None):
        # Store source path for agent module loading
        self.src_path = src_path
        
        # Dictionaries to track agent components and state
        self.agent_states = {}      # Current state of each agent
        self.agent_workers = {}     # Worker objects
        self.agent_threads = {}     # QThread objects
        self.agent_paths = {}       # Paths to agent modules
        self.agent_configs = {}     # Agent-specific configurations
        
        # Signal handlers (to be connected later)
        self.status_handlers = {}    # Callbacks for status updates
        self.message_handlers = {}   # Callbacks for console messages
        self.data_handlers = {}      # Callbacks for data updates
        
        # Initialize agent paths if src_path is provided
        if self.src_path:
            self._initialize_agent_paths()
    
    def _initialize_agent_paths(self):
        """Set up paths to agent modules"""
        self.agent_paths = {
            "copybot": os.path.join(self.src_path, "agents", "copybot_agent.py"),
            "risk": os.path.join(self.src_path, "agents", "risk_agent.py"),
            "dca_staking": os.path.join(self.src_path, "agents", "dca_staking_agent.py"),
            "chart_analysis": os.path.join(self.src_path, "agents", "chartanalysis_agent.py")
        }
        
        # Initialize all agents to INACTIVE state if path exists
        for agent_name, agent_path in self.agent_paths.items():
            if os.path.exists(agent_path):
                self.agent_states[agent_name] = self.STATE_INACTIVE
            else:
                # Just use INACTIVE for errors too to simplify
                self.agent_states[agent_name] = self.STATE_INACTIVE
    
    def register_status_handler(self, agent_name, handler):
        """Register handler for agent status updates"""
        self.status_handlers[agent_name] = handler
    
    def register_message_handler(self, handler):
        """Register handler for console messages"""
        for agent_name in self.agent_paths:
            self.message_handlers[agent_name] = handler
    
    def register_data_handler(self, data_type, handler):
        """Register handler for different types of data updates"""
        self.data_handlers[data_type] = handler
    
    def create_agent_worker(self, agent_name):
        """Create a new worker for the specified agent"""
        # Import here to avoid circular import
        from trading_ui_connected import AgentWorker
        
        if agent_name not in self.agent_paths:
            return None
            
        agent_path = self.agent_paths[agent_name]
        
        # Create worker
        worker = AgentWorker(agent_name, agent_path)
        
        # Create thread
        thread = QThread()
        worker.moveToThread(thread)
        
        # Connect signals
        thread.started.connect(worker.run)
        
        # Connect status updates if handler exists
        if agent_name in self.status_handlers:
            worker.status_update.connect(self.status_handlers[agent_name])
        
        # Connect console messages if handler exists
        if agent_name in self.message_handlers:
            worker.console_message.connect(self.message_handlers[agent_name])
        
        # Connect data handlers if they exist
        for data_type, handler in self.data_handlers.items():
            if data_type == 'portfolio' and hasattr(worker, 'portfolio_update'):
                worker.portfolio_update.connect(handler)
            elif data_type == 'analysis' and hasattr(worker, 'analysis_complete'):
                worker.analysis_complete.connect(handler)
            elif data_type == 'changes' and hasattr(worker, 'changes_detected'):
                worker.changes_detected.connect(handler)
            elif data_type == 'orders' and hasattr(worker, 'order_executed'):
                worker.order_executed.connect(handler)
        
        # Store worker and thread
        self.agent_workers[agent_name] = worker
        self.agent_threads[agent_name] = thread
        
        return worker
    
    def start_agent(self, agent_name):
        """Start an agent, creating a new worker/thread if needed"""
        # Check if agent is already running
        if self.agent_states.get(agent_name) == self.STATE_ACTIVE:
            return False, "Agent is already running"
        
        # Create new worker/thread
        self._cleanup_agent(agent_name)
        
        # Create new worker and thread
        worker = self.create_agent_worker(agent_name)
        if not worker:
            return False, f"Failed to create worker for {agent_name}"
            
        # Start the thread
        thread = self.agent_threads[agent_name]
        thread.start()
        
        # Update state to active
        self.agent_states[agent_name] = self.STATE_ACTIVE
        
        # Special case for dca_staking - also start chart_analysis
        if agent_name == "dca_staking" and "chart_analysis" in self.agent_paths:
            self.start_agent("chart_analysis")
        
        return True, f"Started {agent_name}"
    
    def stop_agent(self, agent_name):
        """Stop an agent gracefully"""
        # Check if agent exists and is running
        if agent_name not in self.agent_workers:
            return False, f"Agent {agent_name} not found"
        
        if self.agent_states.get(agent_name) != self.STATE_ACTIVE:
            return False, f"Agent {agent_name} is not running"
        
        # Get worker and thread
        worker = self.agent_workers[agent_name]
        thread = self.agent_threads[agent_name]
        
        try:
            # Call worker's stop method directly
            worker.stop()
            
            # Update state to inactive immediately
            self.agent_states[agent_name] = self.STATE_INACTIVE
            
            # Wait for thread to finish with timeout
            if thread.isRunning():
                thread.quit()
                success = thread.wait(2000)  # 2 second timeout
                
                # If thread doesn't stop in time, consider more drastic measures
                if not success and thread.isRunning():
                    # This is a last resort to avoid crashed threads
                    if agent_name in self.message_handlers:
                        self.message_handlers[agent_name](f"Thread for {agent_name} did not quit in time", "warning")
            
            # Special case for dca_staking - also stop chart_analysis
            if agent_name == "dca_staking" and "chart_analysis" in self.agent_paths:
                self.stop_agent("chart_analysis")
            
        except Exception as e:
            # Keep state as inactive even on error
            self.agent_states[agent_name] = self.STATE_INACTIVE
            
            # Log error
            if agent_name in self.message_handlers:
                self.message_handlers[agent_name](f"Error stopping {agent_name}: {str(e)}", "error")
        
        return True, f"Stopping {agent_name}"
    
    def restart_agent(self, agent_name):
        """Restart an agent (stop if running, then start)"""
        # If running, stop first
        if self.agent_states.get(agent_name) == self.STATE_ACTIVE:
            success, message = self.stop_agent(agent_name)
            if not success:
                return False, message
                
            # Wait a short time for the agent to stop
            def delayed_start():
                # Give it a short delay
                time.sleep(1)
                
                # Start the agent
                return self.start_agent(agent_name)
            
            # Start in background thread
            restart_thread = threading.Thread(target=delayed_start)
            restart_thread.daemon = True
            restart_thread.start()
            
            return True, f"Restarting {agent_name}"
        else:
            # Not running, just start
            return self.start_agent(agent_name)
    
    def _cleanup_agent(self, agent_name):
        """Clean up agent resources before reinitialization"""
        if agent_name in self.agent_threads:
            thread = self.agent_threads[agent_name]
            worker = self.agent_workers.get(agent_name)
            
            # Disconnect signals if possible
            try:
                if thread.isRunning() and worker:
                    thread.started.disconnect(worker.run)
            except:
                pass
            
            # Stop the thread
            try:
                if thread.isRunning():
                    thread.quit()
                    success = thread.wait(1000)  # 1 second timeout
                    if not success:
                        print(f"Warning: Thread for {agent_name} did not quit in time")
            except Exception as e:
                print(f"Error cleaning up thread for {agent_name}: {str(e)}")
            
            # Remove references
            self.agent_threads.pop(agent_name, None)
            self.agent_workers.pop(agent_name, None)
    
    def stop_all_agents(self):
        """Stop all running agents"""
        for agent_name in list(self.agent_states.keys()):
            if self.agent_states[agent_name] == self.STATE_ACTIVE:
                self.stop_agent(agent_name)
    
    def get_agent_state(self, agent_name):
        """Get the current state of an agent"""
        return self.agent_states.get(agent_name, None)
    
    def get_all_agent_states(self):
        """Get states of all agents"""
        return self.agent_states.copy()