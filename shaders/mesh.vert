#version 450 core
layout(location=0) in vec4 pose; // x,y,z,heading
layout(location=1) in vec4 animation; // source frameA,frameB,blend,aircraft pitch
layout(location=2) in vec4 scale; // instance scale xyz,aircraft bank
layout(location=3) in vec4 identity; // actor ID,side(2 human),role,height/ownership flags:0 relative,1 absolute,2 relative-owned,3 absolute-owned
layout(std430,binding=3) readonly buffer BakedSourceVertices { vec4 sourceVertex[]; };
uniform vec3 camera;
uniform vec4 weather;
uniform vec2 angle;
uniform vec2 projection;
uniform vec2 halfViewport;
uniform ivec2 meshAimClip; // first authored shooting frame,count
uniform ivec2 meshGeometry; // base vec4 offset,vertices per source frame
uniform float meshScale;
uniform int meshMode; // 0 source mesh,1 distant/map glyph,2 real first-person weapon
uniform int tactical;
uniform int censusDetail; // 1 high source,2 low source,3 marker;0 excluded
flat out uint actorCode;
uniform vec2 weaponMotion; // cosmetic recoil, authoritative reload fraction
out vec3 colour;
out float distanceFog;
float height(vec2 p){vec2 q=p-vec2(4000);return 12+q.x*q.x*.000001+q.y*q.y*.0000005+max(0.,1.-abs(q.x)/800.)*18.+terrainRelief(p).x;}
void main(){
 // IDs describe the same geometry/depth as colour, including real occluders.
 // Reject malformed identity data before float-to-integer conversion.
 actorCode=0u;
 if(meshMode!=2 && censusDetail>=1 && censusDetail<=3 &&
    (identity.y==0. || identity.y==1.) && !isnan(identity.x) && !isinf(identity.x) &&
    identity.x>=0. && identity.x<32768. && floor(identity.x)==identity.x)
  actorCode=(uint(censusDetail)<<16)|(uint(identity.x)+1u);
 vec3 local=vec3(0),normal=vec3(0,1,0),material=vec3(.5);
 vec3 team=identity.y==3?vec3(.55,.57,.5):(identity.y==2?vec3(.2,.85,.8):(identity.y==0?vec3(.16,.55,.85):vec3(.9,.25,.12)));
 int poseFlags=int(identity.w);
 bool owned=((poseFlags&3)==2||(poseFlags&3)==3)&&identity.y==0.;
 if(owned)team=vec3(.45,1.,.3);
 if(meshMode!=1){
  int a=meshGeometry.x+(int(animation.x)*meshGeometry.y+gl_VertexID)*3;
  int b=meshGeometry.x+(int(animation.y)*meshGeometry.y+gl_VertexID)*3;
  local=mix(sourceVertex[a].xyz,sourceVertex[b].xyz,animation.z)*scale.xyz*meshScale;
  normal=normalize(mix(sourceVertex[a+1].xyz,sourceVertex[b+1].xyz,animation.z)/max(scale.xyz,vec3(.0001)));
  material=mix(sourceVertex[a+2].rgb,sourceVertex[b+2].rgb,animation.z);
 }
 // Aim is published by the actual visible decision, never chosen here.
 bool infantryAim=meshMode==0&&identity.z==0.&&identity.y<=1.&&(poseFlags&4)!=0&&meshAimClip.y>0;
 if(infantryAim){
  float phase=(poseFlags&8)!=0?min(float(poseFlags>>4)*float(meshAimClip.y)/8.,float(meshAimClip.y-1)):0.;
  int first=meshAimClip.x+int(phase),second=min(first+1,meshAimClip.x+meshAimClip.y-1);
  int aa=meshGeometry.x+(first*meshGeometry.y+gl_VertexID)*3;
  int ab=meshGeometry.x+(second*meshGeometry.y+gl_VertexID)*3;
  int walk=meshGeometry.x+(int(animation.x)*meshGeometry.y+gl_VertexID)*3;
  float weight=clamp(sourceVertex[walk+1].w,0.,1.);
  vec3 upper=mix(sourceVertex[aa].xyz,sourceVertex[ab].xyz,fract(phase))*scale.xyz*meshScale;
  vec3 upperNormal=normalize(mix(sourceVertex[aa+1].xyz,sourceVertex[ab+1].xyz,fract(phase))/max(scale.xyz,vec3(.0001)));
  if(weight>0.){
  local=mix(local,upper,weight);normal=normalize(mix(normal,upperNormal,weight));
  // Body and observed aim headings straddle +/-pi. Wrap their difference
  // before weighting; weighting a nearly full revolution twists waist vertices.
  float aimYaw=scale.w;
  if(aimYaw>3.14159265359)aimYaw-=6.28318530718;
  if(aimYaw< -3.14159265359)aimYaw+=6.28318530718;
  float yaw=aimYaw*weight,pitch=animation.w*weight;
  float c=cos(pitch),s=sin(pitch);mat3 lift=mat3(1,0,0,0,c,-s,0,s,c);
  local=lift*(local-vec3(0,1.35,0))+vec3(0,1.35,0);normal=lift*normal;
  c=cos(yaw);s=sin(yaw);mat3 turn=mat3(c,0,-s,0,1,0,s,0,c);
  local=turn*(local-vec3(0,.85,0))+vec3(0,.85,0);normal=turn*normal;
  }
 }
 // Bank about authored forward +Z, then nose-up pitch, then heading.
 // Nonair instances keep these fields zero, preserving their source clips.
 float cb=cos(scale.w),sb=sin(scale.w),cpAir=cos(animation.w),spAir=sin(animation.w);
 mat3 bank=mat3(cb,sb,0,-sb,cb,0,0,0,1);
 mat3 pitchAir=mat3(1,0,0,0,cpAir,-spAir,0,spAir,cpAir);
 if(!infantryAim){local=pitchAir*bank*local;normal=pitchAir*bank*normal;}
 if(identity.z==4.)team=mix(team,vec3(.8,.86,.9),.22);
 float cy=cos(pose.w),sy=sin(pose.w);
 vec3 world=vec3(cy*local.x+sy*local.z,local.y,-sy*local.x+cy*local.z)+pose.xyz;
 normal=vec3(cy*normal.x+sy*normal.z,normal.y,-sy*normal.x+cy*normal.z);
 if((poseFlags&1)==0)world.y+=height(pose.xz);
 float light=mix(.35,.58,weather.y)+mix(.65,.22,weather.y)*max(0.,dot(normal,normalize(vec3(.35,.85,-.2))));
 colour=mix(material,team,.22)*light;
 if(identity.y==3. && (identity.z==1. || identity.z==2.))colour*=vec3(.35,.32,.29);
 if(identity.y==2)colour=mix(material,team,.35)*light;
 if(meshMode==1)colour=team;
 if(meshMode==2){
  vec3 q=local*.8+vec3(.24,-.42,.95);
  q.z-=min(.08,weaponMotion.x*.4);q.y+=min(.03,weaponMotion.x*.08)-weaponMotion.y*.12;
  gl_Position=vec4(q.x*projection.x,q.y*projection.y,q.z*1.00002-.2,q.z);
  colour=material*(.45+.55*max(0.,normal.y));distanceFog=0;return;
 }
 vec3 p=world-camera;
 if(tactical!=0){
  gl_Position=vec4((world.x-4000)/4300,(world.z-4000)/4300,-world.y/1000,1);distanceFog=0;
 }else{
  float ca=cos(angle.x),sa=sin(angle.x),cp=cos(angle.y),sp=sin(angle.y);
  vec3 q=vec3(ca*p.x-sa*p.z,p.y,sa*p.x+ca*p.z);
  q=vec3(q.x,cp*q.y-sp*q.z,sp*q.y+cp*q.z);
  gl_Position=vec4(q.x*projection.x,q.y*projection.y,q.z*1.00002-.2,q.z);distanceFog=length(p);
 }
 if(meshMode==1){
  const vec2 glyph[3]=vec2[3](vec2(0,1),vec2(-.75,-.7),vec2(.75,-.7));
  float pixels=identity.y==2?5.:(identity.z==0?1.5:2.5);
  if(tactical!=0)pixels=identity.y==2?5.:(identity.z==0?2.:3.5);
  gl_Position.xy+=glyph[gl_VertexID]*vec2(pixels)/halfViewport*gl_Position.w;
 }
}
