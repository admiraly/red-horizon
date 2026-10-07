; Linux SysV ABI. Recorded PCM is signed16 little-endian mono 48000 Hz.
; Fixed preload storage, 128 rotating voices, no hot-path allocation/file loading.
default rel
%define MAX_SAMPLES 192000
%define BANK_BYTES (MAX_SAMPLES*2+2)
%define VOICES 128
%define BLOCK 800
extern snd_pcm_open, snd_pcm_set_params, snd_pcm_writei, snd_pcm_close
extern snd_pcm_avail_update, snd_pcm_recover, getenv
section .rodata
sample_path: db 'content/audio/rifle.pcm',0
explosion_path: db 'content/audio/explosion.pcm',0
footstep_path: db 'content/audio/footstep.pcm',0
engine_path: db 'content/audio/aircraft-engine.pcm',0
device_env: db 'RH_AUDIO_DEVICE',0
default_device: db 'default',0
zero: dd 0.0
one: dd 1.0
half: dd 0.5
q15: dd 32768.0
reference: dd 25.0
engine_reference: dd 150.0
cutoff2: dd 2250000.0
minimum_gain: dd 0.00390625
world_max: dd 8000.0
height_min: dd -1000.0
height_max: dd 2000.0
right_min2: dd 0.25
right_max2: dd 4.0
section .data align=16
listener: dd 0.0,0.0,0.0
listener_right: dd 1.0,0.0
section .bss align=16
samples: resb BANK_BYTES*4
sample_count: resq 4
voice_loop: resd VOICES
voice_loop_owner: resd VOICES
voice_loop_generation: resd VOICES
voice_loop_seen: resd VOICES
global audio_loop_started,audio_loop_updated,audio_loop_stopped
audio_loop_started: resq 1
audio_loop_updated: resq 1
audio_loop_stopped: resq 1
voice_bank: resd VOICES
positions: resd VOICES
next_voice: resd 1
voice_spatial: resd VOICES
voice_x: resd VOICES
voice_y: resd VOICES
voice_z: resd VOICES
voice_gain: resd VOICES
gain_left: resd VOICES
gain_right: resd VOICES
global audio_submitted, audio_culled, audio_replaced, audio_virtualized
global audio_written_frames
audio_written_frames: resq 1
audio_submitted: resq 1
audio_culled: resq 1
audio_replaced: resq 1
audio_virtualized: resd 1
pcm: resq 1
pending: resq 1
pending_offset: resq 1
mix_buffer: resw BLOCK*2
section .text
global audio_init, audio_shot, audio_update, audio_shutdown
global audio_load, audio_mix, audio_active
global audio_listener, audio_emit, audio_emit_kind, audio_load_kind, audio_mix_stereo
; audio_load(RDI=path) -> EAX 0 success / 1 invalid/unreadable.
; Preload only, calls prohibited while mixer executes. Invalid load disables shots.
audio_load:
    mov rsi,rdi
    xor edi,edi
; audio_load_kind(EDI bank0/1/2,RSI path), preload resets voice pool.
audio_load_kind:
    cmp edi,3
    ja .bad
    mov r10d,edi
    mov rdi,rsi
    lea rax,[sample_count]
    mov qword [rax+r10*8],0
    mov qword [pending],0
    mov eax,2
    xor esi,esi
    xor edx,edx
    syscall
    test rax,rax
    js .bad
    mov r8,rax
    xor r9d,r9d
.read:
    xor eax,eax
    mov rdi,r8
    lea rsi,[samples]
    imul rax,r10,BANK_BYTES
    add rsi,rax
    add rsi,r9
    xor eax,eax
    mov edx,MAX_SAMPLES*2+2
    sub rdx,r9
    syscall
    test rax,rax
    js .read_bad
    jz .eof
    add r9,rax
    cmp r9,MAX_SAMPLES*2
    ja .read_bad
    jmp .read
.eof:
    mov eax,3
    mov rdi,r8
    syscall
    test r9,r9
    jz .bad
    test r9b,1
    jnz .bad
    shr r9,1
    lea rax,[sample_count]
    mov [rax+r10*8],r9
    lea rdi,[positions]
    mov eax,-1
    mov ecx,VOICES
    rep stosd
    lea rdi,[voice_loop]
    xor eax,eax
    mov ecx,VOICES
    rep stosd
    mov qword [audio_loop_started],0
    mov qword [audio_loop_updated],0
    mov qword [audio_loop_stopped],0
    mov dword [next_voice],0
    mov qword [audio_written_frames],0
    mov qword [audio_submitted],0
    mov qword [audio_culled],0
    mov qword [audio_replaced],0
    mov dword [audio_virtualized],0
    xor eax,eax
    ret
.read_bad:
    mov eax,3
    mov rdi,r8
    syscall
.bad:
    mov eax,1
    ret
; audio_init() -> EAX 0 ready, 1 invalid content, 2 unavailable device.
; Call once before frame loop. Repeated init requires shutdown first.
audio_init:
    push rbp
    mov rbp,rsp
    push r12
    sub rsp,24
    lea rdi,[sample_path]
    call audio_load
    test eax,eax
    jnz .done
    mov edi,1
    lea rsi,[explosion_path]
    call audio_load_kind
    test eax,eax
    jnz .done
    mov edi,2
    lea rsi,[footstep_path]
    call audio_load_kind
    test eax,eax
    jnz .done
    mov edi,3
    lea rsi,[engine_path]
    call audio_load_kind
    test eax,eax
    jnz .done
    lea rdi,[device_env]
    call getenv wrt ..plt
    test rax,rax
    jnz .name
    lea rax,[default_device]
.name:
    mov rsi,rax
    lea rdi,[pcm]
    xor edx,edx ; playback
    mov ecx,1 ; NONBLOCK
    call snd_pcm_open wrt ..plt
    test eax,eax
    js .unavailable
    mov rdi,[pcm]
    mov esi,2 ; SND_PCM_FORMAT_S16_LE
    mov edx,3 ; SND_PCM_ACCESS_RW_INTERLEAVED
    mov ecx,2 ; stereo output
    mov r8d,48000
    mov r9d,1
    mov qword [rsp],40000 ; latency usec, seventh argument
    call snd_pcm_set_params wrt ..plt
    test eax,eax
    js .close_failed
    xor eax,eax
    jmp .done
.close_failed:
    mov rdi,[pcm]
    call snd_pcm_close wrt ..plt
.unavailable:
    mov qword [pcm],0
    mov eax,2
.done:
    add rsp,24
    pop r12
    pop rbp
    ret
; audio_shot() -> void; sequential frame-thread access only.
; Voice pool saturation replaces oldest submitted shot by rotating slot.
audio_shot:
    cmp qword [sample_count],0
    je shot_done
    push rbp
    mov rbp,rsp
    call allocate_voice
    lea rdx,[voice_bank]
    mov dword [rdx+rax*4],0
    lea rdx,[voice_spatial]
    mov dword [rdx+rax*4],0
    lea rdx,[gain_left]
    mov dword [rdx+rax*4],32768
    lea rdx,[gain_right]
    mov dword [rdx+rax*4],32768
    pop rbp
    ret
shot_done:
    ret
; allocate_voice()->EAX slot, preserves XMM values; rotating bounded replacement.
allocate_voice:
    mov eax,[next_voice]
    lea rdx,[positions]
    mov ecx,[rdx+rax*4]
    test ecx,ecx
    js .free
    lea rdx,[voice_bank]
    mov r11d,[rdx+rax*4]
    lea rdx,[sample_count]
    cmp rcx,[rdx+r11*8]
    jae .free
    inc qword [audio_replaced]
.free:
    lea rdx,[positions]
    inc qword [audio_submitted]
    mov dword [rdx+rax*4],0
    lea rdx,[voice_loop]
    mov dword [rdx+rax*4],0
    lea ecx,[rax+1]
    and ecx,VOICES-1
    mov [next_voice],ecx
    ret
; Validate shared finite world coordinates XMM0=x,XMM1=y,XMM2=z.
; EAX0 valid/-1 invalid; no state writes, no XMM changes.
valid_position:
    ucomiss xmm0,[zero]
    jp .bad
    jb .bad
    ucomiss xmm0,[world_max]
    ja .bad
    ucomiss xmm1,[height_min]
    jp .bad
    jb .bad
    ucomiss xmm1,[height_max]
    ja .bad
    ucomiss xmm2,[zero]
    jp .bad
    jb .bad
    ucomiss xmm2,[world_max]
    ja .bad
    xor eax,eax
    ret
.bad:
    mov eax,-1
    ret
; listener(XMM0=x,XMM1=y,XMM2=z,XMM3=rightx,XMM4=rightz)->0/-1.
; Right vector normalized on submission, rejects nonfinite/degenerate vectors.
audio_listener:
    push rbp
    mov rbp,rsp
    call valid_position
    test eax,eax
    jnz .bad
    movaps xmm5,xmm3
    mulss xmm5,xmm5
    movaps xmm6,xmm4
    mulss xmm6,xmm6
    addss xmm5,xmm6
    ucomiss xmm5,[right_min2]
    jp .bad
    jb .bad
    ucomiss xmm5,[right_max2]
    ja .bad
    sqrtss xmm5,xmm5
    divss xmm3,xmm5
    divss xmm4,xmm5
    movss [listener],xmm0
    movss [listener+4],xmm1
    movss [listener+8],xmm2
    movss [listener_right],xmm3
    movss [listener_right+4],xmm4
    xor eax,eax
    pop rbp
    ret
.bad:
    mov eax,-1
    pop rbp
    ret
; emit(XMM0=x,XMM1=y,XMM2=z,XMM3=gain)->0 submitted/1 culled/-1 invalid.
; Bank0 rifle / bank1 recorded explosion surrogate / bank2 recorded step. No travel delay/occlusion.
audio_emit:
    xor edi,edi
audio_emit_kind:
    push rbp
    mov rbp,rsp
    cmp edi,3
    ja .bad
    call valid_position
    test eax,eax
    jnz .bad
    ucomiss xmm3,[zero]
    jp .bad
    jb .bad
    ucomiss xmm3,[one]
    ja .bad
    lea rax,[sample_count]
    cmp qword [rax+rdi*8],0
    je .bad
    movaps xmm4,xmm0
    subss xmm4,[listener]
    mulss xmm4,xmm4
    movaps xmm5,xmm1
    subss xmm5,[listener+4]
    mulss xmm5,xmm5
    addss xmm4,xmm5
    movaps xmm5,xmm2
    subss xmm5,[listener+8]
    mulss xmm5,xmm5
    addss xmm4,xmm5
    ucomiss xmm4,[cutoff2]
    jae .cull
    ucomiss xmm3,[minimum_gain]
    jb .cull
    call allocate_voice
    lea rdx,[voice_bank]
    mov [rdx+rax*4],edi
    lea rdx,[voice_spatial]
    mov dword [rdx+rax*4],1
    lea rdx,[voice_x]
    movss [rdx+rax*4],xmm0
    lea rdx,[voice_y]
    movss [rdx+rax*4],xmm1
    lea rdx,[voice_z]
    movss [rdx+rax*4],xmm2
    lea rdx,[voice_gain]
    movss [rdx+rax*4],xmm3
    xor eax,eax
    pop rbp
    ret
.cull:
    inc qword [audio_culled]
    mov eax,1
    pop rbp
    ret
.bad:
    mov eax,-1
    pop rbp
    ret
; Recompute <=128 gains once per block after listener moves. Zero-gain voices
; remain logical, advance their cursors, and avoid PCM reads during stereo mix.
prepare_gains:
    mov dword [audio_virtualized],0
    xor r10d,r10d
    lea r8,[positions]
    lea r9,[voice_spatial]
.loop:
    mov eax,[r8+r10*4]
    test eax,eax
    js .next
    lea rdx,[voice_bank]
    mov ecx,[rdx+r10*4]
    lea rdx,[sample_count]
    cmp qword [rdx+rcx*8],0
    je .next
    cmp rax,[rdx+rcx*8]
    jb .gain_ready
    lea rdx,[voice_loop]
    cmp dword [rdx+r10*4],0
    je .next
.gain_ready:
    cmp dword [r9+r10*4],0
    je .next ; legacy local shot remains full gain in both channels
    lea rdx,[voice_x]
    movss xmm0,[rdx+r10*4]
    subss xmm0,[listener]
    lea rdx,[voice_y]
    movss xmm1,[rdx+r10*4]
    subss xmm1,[listener+4]
    lea rdx,[voice_z]
    movss xmm2,[rdx+r10*4]
    subss xmm2,[listener+8]
    movaps xmm3,xmm0
    mulss xmm3,xmm3
    movaps xmm4,xmm1
    mulss xmm4,xmm4
    addss xmm3,xmm4
    movaps xmm4,xmm2
    mulss xmm4,xmm4
    addss xmm3,xmm4
    ucomiss xmm3,[cutoff2]
    jae .virtual
    sqrtss xmm3,xmm3
    movaps xmm4,xmm3
    lea rdx,[voice_loop]
    cmp dword [rdx+r10*4],0
    je .ordinary_reference
    divss xmm4,[engine_reference]
    jmp .reference_done
.ordinary_reference:
    divss xmm4,[reference]
.reference_done:
    addss xmm4,[one]
    lea rdx,[voice_gain]
    movss xmm5,[rdx+r10*4]
    divss xmm5,xmm4 ; inverse distance gain
    ucomiss xmm5,[minimum_gain]
    jb .virtual
    xorps xmm6,xmm6 ; pan at coincident listener/source =center
    ucomiss xmm3,[zero]
    je .pan
    mulss xmm0,[listener_right]
    mulss xmm2,[listener_right+4]
    addss xmm0,xmm2
    divss xmm0,xmm3
    movaps xmm6,xmm0
    minss xmm6,[one]
    movss xmm7,[zero]
    subss xmm7,[one]
    maxss xmm6,xmm7
.pan:
    movss xmm0,[one]
    subss xmm0,xmm6
    mulss xmm0,[half]
    mulss xmm0,xmm5
    mulss xmm0,[q15]
    cvttss2si eax,xmm0
    lea rdx,[gain_left]
    mov [rdx+r10*4],eax
    addss xmm6,[one]
    mulss xmm6,[half]
    mulss xmm6,xmm5
    mulss xmm6,[q15]
    cvttss2si eax,xmm6
    lea rdx,[gain_right]
    mov [rdx+r10*4],eax
    jmp .next
.virtual:
    lea rdx,[gain_left]
    mov dword [rdx+r10*4],0
    lea rdx,[gain_right]
    mov dword [rdx+r10*4],0
    inc dword [audio_virtualized]
.next:
    inc r10d
    cmp r10d,VOICES
    jb .loop
    ret
; mix_stereo(RDI=interleaved int16*,RSI=frames0..800)->frames/-1.
; Writable output frames*4 bytes; Q15 multiply + signed32 channel accumulation.
audio_mix_stereo:
    cmp rsi,BLOCK
    ja .bad
    test rsi,rsi
    jz .zero
    push rbp
    mov rbp,rsp
    push r12
    push r13
    push r14
    push r15
    mov r12,rdi
    mov r13,rsi
    call prepare_gains
    lea r8,[positions]
    lea r9,[samples]
    xor r14d,r14d
.frame:
    xor edi,edi ; left accumulator
    xor esi,esi ; right accumulator
    xor r10d,r10d
.voice:
    mov eax,[r8+r10*4]
    test eax,eax
    js .next
    lea r9,[voice_bank]
    mov r9d,[r9+r10*4]
    lea rdx,[sample_count]
    cmp rax,[rdx+r9*8]
    jb .sample_ready
    cmp qword [rdx+r9*8],0
    je .retire
    lea rdx,[voice_loop]
    cmp dword [rdx+r10*4],0
    je .retire
    xor eax,eax
    mov dword [r8+r10*4],0
.sample_ready:
    imul r9,r9,BANK_BYTES
    lea rdx,[samples]
    add r9,rdx
    inc dword [r8+r10*4]
    lea rdx,[gain_left]
    mov ecx,[rdx+r10*4]
    lea rdx,[gain_right]
    mov r11d,[rdx+r10*4]
    mov edx,ecx
    or edx,r11d
    jz .next ; virtual voice: no sample read, but time advances
    movsx eax,word [r9+rax*2]
    imul ecx,eax
    sar ecx,15
    add edi,ecx
    imul r11d,eax
    sar r11d,15
    add esi,r11d
    jmp .next
.retire:
    mov dword [r8+r10*4],-1
.next:
    inc r10d
    cmp r10d,VOICES
    jb .voice
    mov eax,32767
    cmp edi,eax
    cmovg edi,eax
    cmp esi,eax
    cmovg esi,eax
    mov eax,-32768
    cmp edi,eax
    cmovl edi,eax
    cmp esi,eax
    cmovl esi,eax
    mov [r12+r14*4],di
    mov [r12+r14*4+2],si
    inc r14d
    cmp r14,r13
    jb .frame
    mov eax,r13d
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    ret
.zero:
    xor eax,eax
    ret
.bad:
    mov eax,-1
    ret
; audio_mix(RDI=output int16*, RSI=frames 0..800) -> EAX frames / -1 bound.
; Caller provides writable frames*2 bytes. Signed32 accumulation, signed16 clamp.
; Clobbers volatile registers only. No allocation, libc, file or device calls.
audio_mix:
    cmp rsi,BLOCK
    ja .bad
    mov r11d,esi
    test rsi,rsi
    jz .done
    lea r8,[positions]
    lea r9,[samples]
    xor ecx,ecx
.frame:
    xor edx,edx
    xor r10d,r10d
.voice:
    mov eax,[r8+r10*4]
    test eax,eax
    js .next
    lea r9,[voice_bank]
    mov r9d,[r9+r10*4]
    lea r8,[sample_count]
    cmp rax,[r8+r9*8]
    jb .sample_ready
    cmp qword [r8+r9*8],0
    je .retire_reset
    lea r8,[voice_loop]
    cmp dword [r8+r10*4],0
    je .retire_reset
    xor eax,eax
    lea r8,[positions]
    mov dword [r8+r10*4],0
.sample_ready:
    lea r8,[positions]
    imul r9,r9,BANK_BYTES
    lea r8,[samples]
    add r9,r8
    lea r8,[positions]
    movsx eax,word [r9+rax*2]
    add edx,eax
    inc dword [r8+r10*4]
    jmp .next
.retire_reset:
    lea r8,[positions]
.retire:
    mov dword [r8+r10*4],-1
.next:
    inc r10d
    cmp r10d,VOICES
    jb .voice
    cmp edx,32767
    jle .low
    mov edx,32767
.low:
    cmp edx,-32768
    jge .store
    mov edx,-32768
.store:
    mov [rdi+rcx*2],dx
    inc rcx
    cmp rcx,rsi
    jb .frame
.done:
    mov eax,r11d
    ret
.bad:
    mov eax,-1
    ret
; audio_active() -> EAX count voices with remaining samples, for diagnostics.
audio_active:
    lea rdx,[positions]
    xor eax,eax
    xor ecx,ecx
.loop:
    mov esi,[rdx+rcx*4]
    test esi,esi
    js .next
    lea r8,[voice_bank]
    mov r8d,[r8+rcx*4]
    lea r9,[sample_count]
    cmp qword [r9+r8*8],0
    je .next
    cmp rsi,[r9+r8*8]
    jb .active
    lea r9,[voice_loop]
    cmp dword [r9+rcx*4],0
    je .next
.active:
    inc eax
.next:
    inc ecx
    cmp ecx,VOICES
    jb .loop
    ret
; audio_update() -> void. Nonblocking single-thread pump; <=800 fresh frames.
; Retains partial writes/EAGAIN data. ALSA recovery resets device on underrun.
audio_update:
    cmp qword [pcm],0
    je .return
    push rbp
    mov rbp,rsp
    cmp qword [pending],0
    jne .write
    mov rdi,[pcm]
    call snd_pcm_avail_update wrt ..plt
    test rax,rax
    js .recover
    jz .done
    cmp rax,BLOCK
    jbe .mix
    mov eax,BLOCK
.mix:
    mov rsi,rax
    lea rdi,[mix_buffer]
    call audio_mix_stereo
    mov [pending],rax
    mov qword [pending_offset],0
.write:
    mov rdi,[pcm]
    lea rsi,[mix_buffer]
    mov rax,[pending_offset]
    lea rsi,[rsi+rax*4]
    mov rdx,[pending]
    call snd_pcm_writei wrt ..plt
    test rax,rax
    js .recover
    add [audio_written_frames],rax
    sub [pending],rax
    add [pending_offset],rax
    jmp .done
.recover:
    cmp eax,-11 ; EAGAIN: try retained buffer next frame
    je .done
    mov esi,eax
    mov rdi,[pcm]
    mov edx,1
    call snd_pcm_recover wrt ..plt
.done:
    pop rbp
.return:
    ret
; audio_shutdown() -> void; close outside update, no audio callback exists.
audio_shutdown:
    push rbp
    mov rbp,rsp
    mov rdi,[pcm]
    test rdi,rdi
    jz .done
    call snd_pcm_close wrt ..plt
.done:
    mov qword [pcm],0
    mov qword [sample_count],0
    mov qword [sample_count+8],0
    mov qword [sample_count+16],0
    mov qword [sample_count+24],0
    mov qword [pending],0
    pop rbp
    ret
; Frame-thread persistent recorded source: begin, submit selected sources, end.
; Bank3 shares the existing128 physical voices. No allocation/file/lock/device calls.
global audio_loop_begin,audio_loop_submit,audio_loop_end
audio_loop_begin:
 lea rdi,[voice_loop_seen]
 xor eax,eax
 mov ecx,VOICES
 rep stosd
 ret
; EDI physical owner,ESI generation,XMM0/1/2 position,XMM3 gain.
; EAX0 accepted/1 distance-culled/-1 invalid. Same identity preserves sample cursor.
audio_loop_submit:
 push rbx
 push r12
 sub rsp,8
 mov ebx,edi
 mov r12d,esi
 cmp edi,32768
 jae .bad
 test esi,esi
 jz .bad
 call valid_position
 test eax,eax
 jnz .bad
 ucomiss xmm3,[zero]
 jp .bad
 jb .bad
 ucomiss xmm3,[one]
 ja .bad
 cmp qword [sample_count+24],0
 je .bad
 movaps xmm4,xmm0
 subss xmm4,[listener]
 mulss xmm4,xmm4
 movaps xmm5,xmm1
 subss xmm5,[listener+4]
 mulss xmm5,xmm5
 addss xmm4,xmm5
 movaps xmm5,xmm2
 subss xmm5,[listener+8]
 mulss xmm5,xmm5
 addss xmm4,xmm5
 ucomiss xmm4,[cutoff2]
 jae .cull
 ucomiss xmm3,[minimum_gain]
 jb .cull
 xor eax,eax
.find:
 lea rdx,[voice_loop]
 cmp dword [rdx+rax*4],0
 je .next
 lea rdx,[voice_loop_owner]
 cmp [rdx+rax*4],ebx
 jne .next
 lea rdx,[voice_loop_generation]
 cmp [rdx+rax*4],r12d
 je .existing
 ; Same ID replaced: retire its old generation before allocating a new source.
 lea rdx,[positions]
 mov dword [rdx+rax*4],-1
 lea rdx,[voice_loop]
 mov dword [rdx+rax*4],0
 inc qword [audio_loop_stopped]
.next:
 inc eax
 cmp eax,VOICES
 jb .find
 ; Continuous beds do not evict already playing weapons/impacts.
 xor eax,eax
.free_search:
 lea rdx,[voice_loop]
 cmp dword [rdx+rax*4],0
 jne .free_next
 lea rdx,[positions]
 mov ecx,[rdx+rax*4]
 test ecx,ecx
 js .free_slot
 lea rdx,[voice_bank]
 mov edx,[rdx+rax*4]
 lea r11,[sample_count]
 cmp rcx,[r11+rdx*8]
 jae .free_slot
.free_next:
 inc eax
 cmp eax,VOICES
 jb .free_search
 mov eax,1
 jmp .done
.free_slot:
 mov [next_voice],eax
 call allocate_voice
 inc qword [audio_loop_started]
 lea rdx,[voice_loop]
 mov dword [rdx+rax*4],1
 lea rdx,[voice_loop_owner]
 mov [rdx+rax*4],ebx
 lea rdx,[voice_loop_generation]
 mov [rdx+rax*4],r12d
 lea rdx,[voice_bank]
 mov dword [rdx+rax*4],3
 jmp .store
.existing:
 inc qword [audio_loop_updated]
.store:
 lea rdx,[voice_loop_seen]
 mov dword [rdx+rax*4],1
 lea rdx,[voice_spatial]
 mov dword [rdx+rax*4],1
 lea rdx,[voice_x]
 movss [rdx+rax*4],xmm0
 lea rdx,[voice_y]
 movss [rdx+rax*4],xmm1
 lea rdx,[voice_z]
 movss [rdx+rax*4],xmm2
 lea rdx,[voice_gain]
 movss [rdx+rax*4],xmm3
 xor eax,eax
 jmp .done
.cull:
 mov eax,1
 jmp .done
.bad:
 mov eax,-1
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
audio_loop_end:
 xor eax,eax
.loop:
 lea rdx,[voice_loop]
 cmp dword [rdx+rax*4],0
 je .next
 lea rcx,[voice_loop_seen]
 cmp dword [rcx+rax*4],0
 jne .next
 mov dword [rdx+rax*4],0
 lea rdx,[positions]
 mov dword [rdx+rax*4],-1
 inc qword [audio_loop_stopped]
.next:
 inc eax
 cmp eax,VOICES
 jb .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
