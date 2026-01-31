# Plan: Fix Memory System and Chat Input Visibility

## Problems Identified

### 1. Chat Input Not Visible
- **Cause**: CSS `position: fixed` with `left: 360px` causes the input to be covered or hidden
- **Fix**: Remove fixed positioning, use sticky positioning with proper layout

### 2. Daily Info Feature Not Working
- **Symptom**: Clicking "Daily Info" shows "/daily" but no response
- **Possible Cause**: Chat input overlay might be blocking the response view
- **Fix**: Ensure proper layout so responses are visible

### 3. New Chat Shows Limited Info
- **Symptom**: Only shows greeting "Hallo Benjamin, Chappie v2.0 bereit"
- **Fix**: Enhance greeting with system status, memory count, and personality context

### 4. Debug Mode Issues
- **Symptom**: Debug mode shows no information
- **Fix**: Verify debug state handling and BRAIN MONITOR rendering

## Implementation Plan

### Step 1: Fix Chat Input CSS (styles.py)
```css
/* Remove position: fixed, use sticky with proper layout */
.stChatInputContainer {
    position: sticky !important;
    bottom: 0 !important;
    background-color: var(--bg-color) !important;
    padding: 15px !important;
    z-index: 100 !important;
}
```

### Step 2: Enhance New Chat Greeting (chat_ui.py)
```python
# Add system status, memory info, and personality context
if not st.session_state.messages:
    status = backend.get_status()
    st.markdown(f"### Hallo Benjamin! CHAPPiE v2.0 bereit.")
    st.markdown(f"**System Status:** {status}")
    st.markdown("Womit kann ich dir heute helfen?")
```

### Step 3: Verify Debug Mode (chat_ui.py)
- Check if `debug_mode` state is properly set
- Ensure BRAIN MONITOR component renders correctly

### Step 4: Test All Memory Features
- Daily Info
- Personality
- Consolidate
- Reflect
- New Chat
- Debug Mode
