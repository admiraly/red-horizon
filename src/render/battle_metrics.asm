; Read-only per-render-frame diagnostics. Submission counts are not visibility.
default rel
extern sim_alive,sim_engaged,sim_projectile_count
extern mesh_high_instances,mesh_low_instances,mesh_marker_instances
extern effects_active,air_trails_active,audio_active,printf
section .bss
align 16
global battle_metrics_last,battle_metrics_peak,battle_metrics_samples,battle_metrics_simultaneous
battle_metrics_last: resd 9
battle_metrics_peak: resd 9
battle_metrics_samples: resq 1
battle_metrics_simultaneous: resq 1
section .rodata
format: db '{"battle_metrics":true,"samples":%lu,"simultaneous_projectiles_effects_audio_frames":%lu,"peak_living":%u,"peak_engaged":%u,"peak_projectiles":%u,"peak_submitted_high":%u,"peak_submitted_low":%u,"peak_submitted_markers":%u,"peak_effect_records":%u,"peak_trail_records":%u,"peak_audio_voices":%u,"visible_individual_count":"unmeasured","scope":"frame samples; independent peaks need not coincide; submitted models are not pixel visibility"}',10,0
section .text
global battle_metrics_reset,battle_metrics_capture,battle_metrics_report
battle_metrics_reset:
 lea rdi,[battle_metrics_last]
 xor eax,eax
 mov ecx,22
 rep stosd
 ret
; Called after cosmetic updates and draws, before the CPU frame timer ends.
battle_metrics_capture:
 sub rsp,8
 mov eax,[sim_alive]
 add eax,[sim_alive+4]
 mov [battle_metrics_last],eax
 mov eax,[sim_engaged]
 mov [battle_metrics_last+4],eax
 mov eax,[sim_projectile_count]
 mov [battle_metrics_last+8],eax
 mov eax,[mesh_high_instances]
 mov [battle_metrics_last+12],eax
 mov eax,[mesh_low_instances]
 mov [battle_metrics_last+16],eax
 mov eax,[mesh_marker_instances]
 mov [battle_metrics_last+20],eax
 mov eax,[effects_active]
 mov [battle_metrics_last+24],eax
 mov eax,[air_trails_active]
 mov [battle_metrics_last+28],eax
 call audio_active
 mov [battle_metrics_last+32],eax
 lea rdx,[battle_metrics_last]
 lea rsi,[battle_metrics_peak]
 xor ecx,ecx
.loop:
 mov eax,[rdx+rcx*4]
 cmp eax,[rsi+rcx*4]
 jbe .next
 mov [rsi+rcx*4],eax
.next:
 inc ecx
 cmp ecx,9
 jb .loop
 inc qword [battle_metrics_samples]
 cmp dword [battle_metrics_last+8],0
 je .done
 cmp dword [battle_metrics_last+24],0
 je .done
 test eax,eax
 ; EAX at loop end is audio voice count.
 jz .done
 inc qword [battle_metrics_simultaneous]
.done:
 add rsp,8
 ret
battle_metrics_report:
 sub rsp,56
 lea rdi,[format]
 mov rsi,[battle_metrics_samples]
 mov rdx,[battle_metrics_simultaneous]
 mov ecx,[battle_metrics_peak]
 mov r8d,[battle_metrics_peak+4]
 mov r9d,[battle_metrics_peak+8]
 %assign i 0
 %rep 6
 mov eax,[battle_metrics_peak+12+i*4]
 mov [rsp+i*8],rax
 %assign i i+1
 %endrep
 xor eax,eax
 call printf
 add rsp,56
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
