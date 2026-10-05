#version 450 core
layout(location=0) in vec4 pose; // x,y,z,heading
layout(location=1) in vec4 animation; // source frameA,frameB,blend,aircraft pitch
layout(location=2) in vec4 scale; // instance scale xyz,aircraft bank
layout(location=3) in vec4 identity; // actor ID,side(2 human),role,absolute-y flag
layout(std430,binding=3) readonly buffer BakedSourceVertices { vec4 sourceVertex[]; };
uniform vec3 camera;
uniform vec4 weather;
uniform vec2 angle;
uniform vec2 projection;
uniform vec2 halfViewport;
uniform ivec2 meshGeometry; // base vec4 offset,vertices per source frame
uniform float meshScale;
uniform int meshMode; // 0 source mesh,1 distant/map glyph,2 real first-person weapon
uniform int tactical;
uniform vec2 weaponMotion; // cosmetic recoil, authoritative reload fraction
out vec3 colour;
out float distanceFog;
float height(vec2 p){vec2 q=p-vec2(4000);return 12+q.x*q.x*.000001+q.y*q.y*.0000005+max(0.,1.-abs(q.x)/800.)*18.;}
void main(){
 vec3 local=vec3(0),normal=vec3(0,1,0),material=vec3(.5);
 vec3 team=identity.y==3?vec3(.55,.57,.5):(identity.y==2?vec3(.2,.85,.8):(identity.y==0?vec3(.16,.55,.85):vec3(.9,.25,.12)));
 if(meshMode!=1){
  int a=meshGeometry.x+(int(animation.x)*meshGeometry.y+gl_VertexID)*3;
  int b=meshGeometry.x+(int(animation.y)*meshGeometry.y+gl_VertexID)*3;
  local=mix(sourceVertex[a].xyz,sourceVertex[b].xyz,animation.z)*scale.xyz*meshScale;
  normal=normalize(mix(sourceVertex[a+1].xyz,sourceVertex[b+1].xyz,animation.z)/max(scale.xyz,vec3(.0001)));
  material=mix(sourceVertex[a+2].rgb,sourceVertex[b+2].rgb,animation.z);
 }
 // Bank about authored forward +Z, then nose-up pitch, then heading.
 // Nonair instances keep these fields zero, preserving their source clips.
 float cb=cos(scale.w),sb=sin(scale.w),cpAir=cos(animation.w),spAir=sin(animation.w);
 mat3 bank=mat3(cb,sb,0,-sb,cb,0,0,0,1);
 mat3 pitchAir=mat3(1,0,0,0,cpAir,-spAir,0,spAir,cpAir);
 local=pitchAir*bank*local;normal=pitchAir*bank*normal;
 if(identity.z==4.)team=mix(team,vec3(.8,.86,.9),.22);
 float cy=cos(pose.w),sy=sin(pose.w);
 vec3 world=vec3(cy*local.x+sy*local.z,local.y,-sy*local.x+cy*local.z)+pose.xyz;
 normal=vec3(cy*normal.x+sy*normal.z,normal.y,-sy*normal.x+cy*normal.z);
 if(identity.w==0)world.y+=height(pose.xz);
 float light=mix(.35,.58,weather.y)+mix(.65,.22,weather.y)*max(0.,dot(normal,normalize(vec3(.35,.85,-.2))));
 colour=mix(material,team,.22)*light;
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
